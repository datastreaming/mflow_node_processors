import json
import os
from collections import OrderedDict
from logging import getLogger

import bottle
from bottle import request, run, Bottle, static_file, response, template

_logger = getLogger(__name__)

API_PATH_FORMAT = "/api/v1/{instance_name}/{{url}}"
HTML_PATH_FORMAT = "/{instance_name}/{{url}}"


def start_web_interface(process, instance_name, host, port):
    """
    Start the web interface for the supplied external process.
    :param process: External process to communicate with.
    :param instance_name: Name if this processor instance. Used to set url paths.
    :param host: Host to start the web interface on.
    :param port: Port to start the web interface on.
    :return: None
    """
    app = Bottle()
    static_root_path = os.path.join(os.path.dirname(__file__), "static")
    _logger.debug("Static files root folder: %s", static_root_path)

    # Set the path for the templates.
    bottle.TEMPLATE_PATH = [static_root_path]

    # Set the URL paths based on the format and instance name.
    api_path = API_PATH_FORMAT.format(instance_name=instance_name)
    html_path = HTML_PATH_FORMAT.format(instance_name=instance_name)

    @app.get("/")
    def redirect_to_index():
        return bottle.redirect(html_path.format(url=""))

    @app.get(html_path.format(url=""))
    @bottle.view("index")
    def index():
        return {"instance_name": instance_name}

    @app.get(api_path.format(url="help"))
    def get_help():
        return {"status": "ok",
                "data": process.get_process_help()}

    @app.get(api_path.format(url="status"))
    def get_status():
        return {"status": "ok",
                "data": {"processor_name": process.get_process_name(),
                         "is_running": process.is_running(),
                         "parameters": get_parameters()["data"]}}

    @app.get(api_path.format(url="statistics"))
    def get_statistics():
        return {"status": "ok",
                "data": {"statistics": process.get_statistics()}}

    @app.get(api_path.format(url="statistics_raw"))
    def get_statistics_raw():
        return {"status": "ok",
                "data": {"processing_times": process.get_statistics_raw()}}

    @app.get(api_path.format(url="parameters"))
    def get_parameters():
        return {"status": "ok",
                "data": process.get_parameters()}

    def _set_parameters(items):
        for parameter in items:
            _logger.debug("Passing parameter '%s'='%s' to external process." % parameter)
            process.set_parameter(parameter)

    @app.post(api_path.format(url="parameters"))
    def set_parameter():
        _set_parameters(request.json.items())
        return {"status": "ok",
                "message": "Parameters set successfully."}

    @app.put(api_path.format(url=""))
    @app.get(api_path.format(url="start"))
    def start():
        if request.json:
            _set_parameters(request.json.items())

        _logger.debug("Starting process.")
        process.start()

        return {"status": "ok",
                "message": "Process started."}

    @app.delete(api_path.format(url=""))
    @app.get(api_path.format(url="stop"))
    def stop():
        _logger.debug("Stopping process.")
        process.stop()

        return {"status": "ok",
                "message": "Process stopped."}

    @app.get(html_path.format(url="static/<filename:path>"))
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
    """
    Base class for all classes that interact with the Bottle instance.
    """

    def get_process_name(self):
        """
        Return the process name.
        :return: String representation of the name.
        """
        return getattr(self, "__name__", self.__class__.__name__)

    def get_process_help(self):
        """
        Return the processor documentation.
        :return:
        """
        return self.__doc__ or "Sorry, no help available."

    def start(self):
        """
        Start the processor.
        """
        pass

    def stop(self):
        """
        Stop the processor.
        :return:
        """
        pass

    def is_running(self):
        """
        Check if the process is running.
        :return: True if the process is running, False otherwise.
        """
        pass

    def get_parameters(self):
        """
        Get process parameters.
        :return: Dictionary with all the parameters.
        """
        return OrderedDict((key, value) for key, value
                           in sorted(vars(self).items())
                           if not key.startswith('_'))

    def set_parameter(self, parameter):
        """
        Set the parameters on the process.
        :param parameter: Parameter to set, in (parameter_name, parameter_value) form.
        """
        pass

    def get_statistics(self):
        """
        Get the processor statistics.
        :return: Dictionary of relevant statistics.
        """
        return self.get_statistics_raw()

    def get_statistics_raw(self):
        """
        Get the processor raw statistics data.
        :return: List of statistics events.
        """
        pass