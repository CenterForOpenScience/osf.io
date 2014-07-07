# -*- coding: utf-8 -*-

import abc

from .base import BaseService, ServiceError


class HookService(BaseService):

    @abc.abstractmethod
    def create(self):
        pass

    @abc.abstractmethod
    def delete(self):
        pass


class HookServiceError(ServiceError):
    pass


class HookExistsError(HookServiceError):
    pass


class NoHookError(HookServiceError):
    pass
