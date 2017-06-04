# -*- coding: utf-8 -*-
"""Factory boy factories for the Dropbox addon."""

from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.dropbox.model import (
    DropboxUserSettings, DropboxNodeSettings
)


class DropboxUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = DropboxUserSettings

    owner = SubFactory(UserFactory)
    access_token = Sequence(lambda n: 'abcdef{0}'.format(n))


class DropboxNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = DropboxNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(DropboxUserSettingsFactory)
    folder = 'Camera Uploads'

class DropboxAccountFactory(ExternalAccountFactory):
    provider = 'dropbox'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
