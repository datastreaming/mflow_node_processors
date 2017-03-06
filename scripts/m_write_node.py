import logging
import sys
from argparse import ArgumentParser

from bitshuffle.h5 import H5_COMPRESS_LZ4
from mflow_nodes.stream_node import start_stream_node
from mflow_processor.h5_chunked_writer import HDF5ChunkedWriterProcessor

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger("mflow.mflow").setLevel(logging.ERROR)

parser = ArgumentParser()
parser.add_argument("instance_name", type=str, help="Name of the node instance. Should be unique.")
parser.add_argument("listening_address", type=str, help="Listening address for mflow connection.\n"
                                                        "Example: tcp://127.0.0.1:40001")
parser.add_argument("--output_file", type=str, help="Name of output h5 file to write.")
parser.add_argument("--rest_port", type=int, default=41001, help="Port for web interface.")
parser.add_argument("--raw", action='store_true', help="Receive the mflow messages in raw mode.")
input_args = parser.parse_args()

parameters = {"dataset_name": "entry/data/data",
              "compression": 32008,
              "compression_opts": (2048, H5_COMPRESS_LZ4)
              }

if input_args.output_file:
    parameters["output_file"] = input_args.output_file

start_stream_node(instance_name=input_args.instance_name,
                  processor=HDF5ChunkedWriterProcessor(),
                  processor_parameters=parameters,
                  listening_address=input_args.listening_address,
                  control_port=input_args.rest_port,
                  receive_raw=input_args.raw)
