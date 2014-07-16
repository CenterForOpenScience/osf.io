# -*- coding: utf-8 -*-

import abc

from .base import BaseService, ServiceError


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

    @abc.abstractmethod
    def list_files(self, path):
        pass


class FileServiceError(ServiceError):
    pass


class FileTooLargeError(FileServiceError):
    pass


class FileEmptyError(FileServiceError):
    pass


class FileUploadError(FileServiceError):
    pass


class ListFilesError(FileServiceError):
    pass


class FileDownloadError(FileServiceError):
    pass


class FileDeleteError(FileServiceError):
    pass
