# encoding: utf-8

class WaterButlerException(Exception):
    pass


class CouldNotServerStreamError(WaterButlerException):
    pass


class FileNotFoundError(CouldNotServerStreamError):
    pass
