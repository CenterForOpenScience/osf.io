# encoding: utf-8


class ProviderException(Exception):
    pass


class CouldNotServeStreamError(ProviderException):
    pass


class FileNotFoundError(CouldNotServeStreamError):
    pass
