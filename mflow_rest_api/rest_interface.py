import json
import os
from collections import OrderedDict
from logging import getLogger
from bottle import request, run, Bottle, static_file, response

_logger = getLogger(__name__)


def start_web_interface(process, host, port):
    """
    Start the web interface for the supplied external process.
    :param process: External process to communicate with.
    :param host: Host to start the web interface on.
    :param port: Port to start the web interface on.
    :return: None
    """
    app = Bottle()
    static_root_path = os.path.join(os.path.dirname(__file__), "static")

    @app.get("/")
    def index():
        return static_file(filename="index.html", root=static_root_path)

    @app.get("/help")
    def get_help():
        return {"status": "ok",
                "data": process.get_process_help()}

    @app.get("/status")
    def get_status():
        return {"status": "ok",
                "data": {"processor_name": process.get_process_name(),
                         "is_running": process.is_running(),
                         "parameters": get_parameters()["data"]}}

    @app.get("/statistics")
    def get_statistics():
        return {"status": "ok",
                "data": {"statistics": process.get_statistics()}}

    @app.get("/statistics_raw")
    def get_statistics_raw():
        return {"status": "ok",
                "data": {"processing_times": process.get_statistics_raw()}}

    @app.get("/parameters")
    def get_parameters():
        return {"status": "ok",
                "data": process.get_parameters()}

    @app.post("/parameters")
    def set_parameter():
        for parameter in request.json.items():
            _logger.debug("Passing parameter '%s'='%s' to external process." % parameter)
            process.set_parameter(parameter)

        return {"status": "ok",
                "message": "Parameters set successfully."}

    @app.get("/start")
    def start():
        _logger.debug("Starting process.")
        process.start()

        return {"status": "ok",
                "message": "Process started."}

    @app.get("/stop")
    def stop():
        _logger.debug("Stopping process.")
        process.stop()

        return {"status": "ok",
                "message": "Process stopped."}

    @app.get("/static/<filename:path>")
    def get_static(filename):
        return static_file(filename=filename, root=static_root_path)

    @app.error(500)
    def error_handler_500(error):
        response.content_type = 'application/json'
        response.status = 200

        return json.dumps({"status": "error",
                           "message": str(error.exception)})

    try:
        run(app=app, host=host, port=port)
    finally:
        # Close the external processor when terminating the web server.
        if process.is_running():
            process.stop()


class RestInterfacedProcess(object):
    def get_process_name(self):
        return getattr(self, "__name__", self.__class__.__name__)

    def get_process_help(self):
        return self.__doc__ or "Sorry, no help available."

    def start(self):
        pass

    def stop(self):
        pass

    def is_running(self):
        pass

    def get_parameters(self):
        return OrderedDict((key, value) for key, value
                           in sorted(vars(self).items())
                           if not key.startswith('_'))

    def set_parameter(self, parameter):
        pass

    def get_statistics(self):
        return self.get_statistics_raw()

    def get_statistics_raw(self):
        pass