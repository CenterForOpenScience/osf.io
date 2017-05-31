# -*- coding: utf-8 -*-
"""Factory boy factories for the Forward addon."""

from factory import SubFactory
from factory.django import DjangoModelFactory
from osf_tests.factories import ProjectFactory

from addons.forward.models import NodeSettings


class ForwardSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = SubFactory(ProjectFactory)
    url = 'http://frozen.pizza.reviews/'
