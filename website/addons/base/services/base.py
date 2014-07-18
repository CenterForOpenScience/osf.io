# -*- coding: utf-8 -*-

import abc
import six


class ServiceError(Exception):
    pass


class ServiceConfigurationError(ServiceError):
    pass


@six.add_metaclass(abc.ABCMeta)
class BaseService(object):

    def __init__(self, addon_model):
        self.addon_model = addon_model
