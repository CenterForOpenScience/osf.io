import abc


class BaseAuthHandler(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def fetch(self, request_handler):
        pass
