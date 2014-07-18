# -*- coding: utf-8 -*-

from website.addons.base.services.base import ServiceConfigurationError


def assert_provisioned(addon_model, provisioned):
    if addon_model.provisioned != provisioned:
        raise ServiceConfigurationError()
