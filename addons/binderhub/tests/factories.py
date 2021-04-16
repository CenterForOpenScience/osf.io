"""Factories for the My Screen addon."""
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import ProjectFactory

from ..models import NodeSettings


class NodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
