class WaterButlerException(Exception):
    pass


class CouldNotServerStreamError(WaterButlerException):
    pass


class FileNotFoundError(CouldNotServerStreamError):
    pass
