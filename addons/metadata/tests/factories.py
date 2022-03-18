# -*- coding: utf-8 -*-
"""Factories for the metadata addon."""
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import ProjectFactory

from ..models import NodeSettings


class NodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model =  NodeSettings

    owner = factory.SubFactory(ProjectFactory)
