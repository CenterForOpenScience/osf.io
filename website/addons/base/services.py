# -*- coding: utf-8 -*-

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class BaseService(object):

    def __init__(self, addon_model):
        self.addon_model = addon_model


class FileService(BaseService):

    @abc.abstractmethod
    def upload(self, path, filelike, **kwargs):
        pass

    @abc.abstractmethod
    def download(self, path, **kwargs):
        pass

    @abc.abstractmethod
    def delete(self, path, **kwargs):
        pass


class HookService(BaseService):

    @abc.abstractmethod
    def create(self):
        pass

    @abc.abstractmethod
    def delete(self):
        pass


# exceptions.py


class ServiceError(Exception):
    pass


class FileServiceError(ServiceError):
    pass


class FileTooLargeError(FileServiceError):
    pass


class FileEmptyError(FileServiceError):
    pass


class FileUploadError(FileServiceError):
    pass


class FileDownloadError(FileServiceError):
    pass


class FileDeleteError(FileServiceError):
    pass