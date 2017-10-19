import h5py
from logging import getLogger

from mflow_nodes.processors.base import BaseProcessor

from mflow_processor.utils.h5_utils import populate_h5_file, create_dataset, compact_dataset, expand_dataset, \
    set_dataset_attributes


class HDF5ChunkedWriterProcessor(BaseProcessor):
    """
    H5 chunked writer

    Writes the received stream to a HDF5 file.

    Writer commands:
        start                          Starts the writer, overwriting the output file if exists.
        stop                           Stop the writer, compact the dataset and close the file.

    Writer parameters:

        dataset_name                   Name of the dataset to write the data inside the H5 file.
        frame_size                     Size of a single frame in pixels.
        dtype                          Data type of the stream.
        output_file                    Location to write the H5 file to.

        compression                    Filter number to be used. None for no compression. None is default.
        compression_opts               Options to pass to the compression filter. None is default.

        h5_group_attributes            Attributes to add to the H5 file groups.
        h5_dataset_attributes          Attributes to add the the H5 datasets.
        h5_datasets                    Datasets to add to the H5 file.
    """
    _logger = getLogger(__name__)

    def __init__(self, name="H5 chunked writer", plugins=None):
        """
        Initialize the chunked writer.
            :param name: Name of the writer.
        """
        self.__name__ = name

        self._file = None
        self._dataset = None
        self._max_frame_index = 0
        self._current_frame_chunk = None
        self._plugins = plugins or []

        # Parameters that need to be set.
        self.dataset_name = None
        self.output_file = None

        # Parameters with default values.
        self.frames_per_file = None
        self.compression = None
        self.compression_opts = None

        # Additional H5 datasets and attributes.
        self.h5_group_attributes = {}
        self.h5_dataset_attributes = {}
        self.h5_datasets = {}

    def _validate_parameters(self):
        """
        Check if all the needed parameters are set.
        :return: ValueError if any parameter is missing.
        """
        error_message = ""

        if not self.dataset_name:
            error_message += "Parameter 'dataset_name' not set.\n"

        if not self.output_file:
            error_message += "Parameter 'output_file' not set.\n"

        if error_message:
            self._logger.error(error_message)
            raise ValueError(error_message)

    def start(self):
        self._logger.debug("Writer started.")
        # Check if all the needed input parameters are available.
        self._validate_parameters()
        self._logger.debug("Starting mflow_processor.")

    def _create_file(self, frame_size, dtype, frame_chunk=0):
        """
        Create a new H5 file for the provided frame_chunk.
        :param frame_chunk: The number of the data file to write to.
        """
        if self._file:
            self._close_file()

        filename = self.output_file.format(chunk_number=frame_chunk)
        self._logger.debug("Writing to file '%s' chunks of size %s." % (filename, frame_size))

        # Truncate file if it already exists.
        self._file = h5py.File(filename, "w")

        # Construct the dataset.
        self._dataset = create_dataset(self._file,
                                       self.dataset_name,
                                       frame_size,
                                       dtype,
                                       self.compression,
                                       self.compression_opts)
        # Record the dataset size for later comparison.
        self._current_dataset_size = self._dataset.shape[0]

        self._current_frame_chunk = frame_chunk

    def _set_data_chunk_attributes(self):
        """
        Insert the lowest and highest frame index attribute to the frame dataset.
        """
        if self.frames_per_file:
            min_frame_in_dataset = (self._current_frame_chunk - 1) * self.frames_per_file
        else:
            min_frame_in_dataset = 0
        max_frame_in_dataset = self._max_frame_index + min_frame_in_dataset

        # Do not display the index number, but the the frame number (starts with 1)
        set_dataset_attributes(self._file, {"%s:%s" % (self.dataset_name, "image_nr_low"): min_frame_in_dataset + 1,
                                            "%s:%s" % (self.dataset_name, "image_nr_high"): max_frame_in_dataset + 1})

    def _close_file(self):
        """
        Close the current file. Compact the dataset and write the needed metadata to the H5 file.s
        """
        compact_dataset(self._dataset, self._max_frame_index)
        # Set the minimum and the maximum frame in the current dataset.
        self._set_data_chunk_attributes()
        # Additional datasets and group and dataset attributes.
        populate_h5_file(self._file, self.h5_group_attributes, self.h5_datasets, self.h5_dataset_attributes)

        self._file.close()
        self._file = None
        self._current_frame_chunk = None
        self._max_frame_index = 0

    def _prepare_storage_for_frame(self, frame_index, frame_size, dtype):
        """
        Takes care of preparing the correct storage destination for the provided frame index.
        :param frame_index: Index of the received frame.
        :param frame_size: Size of the frame.
        :param dtype: Frame data type.
        :return: Relative frame index to be used inside the prepared dataset.
        """

        # If the image does not belong to the current file chunk, close the file and create a new one.
        if self.frames_per_file:
            frame_chunk = (frame_index // self.frames_per_file) + 1
            if not self._current_frame_chunk == frame_chunk:
                self._create_file(frame_size, dtype, frame_chunk)

            frame_index -= (frame_chunk - 1) * self.frames_per_file
        # The file is not open yet.
        elif self._file is None:
            self._create_file(frame_size, dtype)

        # If the current frame does not fit in the dataset, expand it.
        if not frame_index < self._current_dataset_size:
            self._current_dataset_size = expand_dataset(self._dataset, frame_index)

        # Keep track of the max frame index to shrink the dataset before closing it.
        if frame_index > self._max_frame_index:
            self._max_frame_index = frame_index

        return frame_index

    def process_message(self, message):
        frame_index = message.get_frame_index()
        relative_frame_index = self._prepare_storage_for_frame(frame_index,
                                                               message.get_frame_size(),
                                                               message.get_frame_dtype())

        self._logger.debug("Received frame '%d', writing as relative frame '%d'.", frame_index, relative_frame_index)

        frame_data = message.get_data()
        # Because the conversion to and from bytes is slow, mflow should be used in raw mode.
        bytes_to_write = frame_data if isinstance(frame_data, bytes) else frame_data.tobytes()
        self._dataset.id.write_direct_chunk((relative_frame_index, 0, 0), bytes_to_write)

        # Process additional plugins on the message.
        for plugin_function in self._plugins:
            plugin_function(self, message)

    def stop(self):
        self._logger.debug("Writer stopped.")

        if self._file:
            self._close_file()
