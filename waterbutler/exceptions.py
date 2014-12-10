# encoding: utf-8

from tornado.web import HTTPError


class WaterButlerException(HTTPError):
    def __init__(self, message, code=500, log_message=None):
        super().__init__(code, log_message=log_message, reason=message)


class ProviderException(WaterButlerException):
    pass


class FileNotFoundError(ProviderException):
    def __init__(self, path):
        super().__init__(404, reason='Could not retrieve file or directory {0}'.format(message))
