# -*- coding: utf-8 -*-
"""Factories for the dryad addon."""
from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.dryad.model import (
    DryadUserSettings,
    DryadNodeSettings
)

class DryadAccountFactory(ExternalAccountFactory):
    provider = 'dryad'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n: 'secret-{0}'.format(n))
    display_name = 'Dryad Fake User'


class DryadUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = DryadUserSettings

    owner = SubFactory(UserFactory)


class DryadNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = DryadNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(DryadUserSettingsFactory)
