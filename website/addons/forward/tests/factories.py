# -*- coding: utf-8 -*-
"""Factory boy factories for the Dropbox addon."""

from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory

from website.addons.forward.model import (
    ForwardNodeSettings
)


class ForwardSettingsFactory(ModularOdmFactory):

    FACTORY_FOR = ForwardNodeSettings

    owner = SubFactory(ProjectFactory)
    url = 'http://frozen.pizza.reviews/'
    redirect_bool = True
    redirect_secs = 15
