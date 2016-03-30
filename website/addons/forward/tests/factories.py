# -*- coding: utf-8 -*-
"""Factory boy factories for the Forward addon."""

from factory import SubFactory
from tests.factories import ModularOdmFactory, ProjectFactory

from website.addons.forward.model import ForwardNodeSettings


class ForwardSettingsFactory(ModularOdmFactory):
    class Meta:
        model = ForwardNodeSettings

    owner = SubFactory(ProjectFactory)
    url = 'http://frozen.pizza.reviews/'
    redirect_bool = True
    redirect_secs = 15
