from argparse import ArgumentParser

from mflow_nodes.script_tools.helpers import add_default_arguments, setup_console_logging, start_stream_node_helper
from mflow_processor.h5_nxmx_writer import HDF5nxmxWriter


def run(input_args, parameters=None):
    start_stream_node_helper(HDF5nxmxWriter(h5_writer_control_address=input_args.writer_control_address,
                                            h5_writer_instance_name=input_args.writer_instance_name),
                             input_args, parameters)


if __name__ == "__main__":
    setup_console_logging()

    parser = ArgumentParser()
    add_default_arguments(parser, binding_argument=True)
    parser.add_argument("writer_control_address", type=str, help="URL of the H5 writer node REST Api.\n"
                                                                 "Example: http://127.0.0.1:41001")
    parser.add_argument("writer_instance_name", type=str, help="Name of the writer instance name.")

    run(parser.parse_args())
