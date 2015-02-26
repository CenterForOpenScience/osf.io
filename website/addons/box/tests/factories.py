# -*- coding: utf-8 -*-
"""Factory boy factories for the Box addon."""
import mock
from datetime import datetime

from framework.auth import Auth

from factory import SubFactory, Sequence, post_generation
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory

from website.addons.box.model import (
    BoxOAuthSettings, BoxUserSettings,
    BoxNodeSettings, BoxFile
)

# TODO(sloria): make an abstract UserSettingsFactory that just includes the owner field

class BoxOAuthSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = BoxOAuthSettings

    username = 'Den'
    user_id = 'b4rn311'
    expires_at = datetime(2045, 1, 1)
    access_token = Sequence(lambda n: 'abcdef{0}'.format(n))
    refresh_token = Sequence(lambda n: 'abcdef{0}'.format(n))


class BoxUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = BoxUserSettings

    owner = SubFactory(UserFactory)
    oauth_settings = SubFactory(BoxOAuthSettingsFactory)


class BoxNodeSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = BoxNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(BoxUserSettingsFactory)
    with mock.patch('website.addons.box.model.BoxNodeSettings.folder') as mock_folder:
        mock_folder.__get__ = mock.Mock(return_value='Camera Uploads')


class BoxFileFactory(ModularOdmFactory):
    FACTORY_FOR = BoxFile

    node = SubFactory(ProjectFactory)
    path = 'foo.txt'

    @post_generation
    def add_box_addon(self, created, extracted):
        self.node.add_addon('box', auth=Auth(user=self.node.creator))
        self.node.save()
