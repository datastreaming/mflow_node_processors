from logging import getLogger
from mflow_node.processor import StreamProcessor, MFlowForwarder


class ProxyProcessor(StreamProcessor):
    """
    MFlow Proxy

    Executes the provided function on the received packages and forwards the original
    package to the next node.

    Proxy commands:
        start                          Starts the proxy.
        stop                           Stop the proxy.

    Proxy parameters:
        forwarding_address             Address to forward the stream to.
    """
    _logger = getLogger(__name__)

    def __init__(self, proxy_function, name="Proxy node"):
        self._zmq_forwarder = None
        self._proxy_function = proxy_function
        self.__name__ = name

        # Parameters to set.
        self.forwarding_address = None

    def _validate_parameters(self):
        error_message = ""

        if not self.forwarding_address:
            error_message += "Parameter 'forwarding_address' not set.\n"

        if not callable(self._proxy_function):
            error_message += "Parameter 'proxy_function' is not a valid function\n"

        if error_message:
            self._logger.error(error_message)
            raise ValueError(error_message)

    def start(self):
        self._logger.debug("Proxy started.")
        # Check if all the needed input parameters are available.
        self._validate_parameters()

        self._logger.debug("Stream forwarding address='%s'." % self.forwarding_address)
        self._zmq_forwarder = MFlowForwarder()
        self._zmq_forwarder.start(self.forwarding_address)

    def process_message(self, message):
        self._logger.debug("Received frame '%d'. Passing to proxy function." % message.get_frame_index())
        forward_message = self._proxy_function(message)

        # If the proxy function returned data, forward this.
        if forward_message:
            self._zmq_forwarder.send(message)

    def stop(self):
        self._zmq_forwarder.stop()
