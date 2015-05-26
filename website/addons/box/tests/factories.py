# -*- coding: utf-8 -*-
"""Factory boy factories for the Box addon."""
import mock
from datetime import datetime
from dateutil.relativedelta import relativedelta

from framework.auth import Auth

from factory import SubFactory, post_generation, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.box.model import (
    BoxUserSettings,
    BoxNodeSettings, BoxFile
)

# TODO(sloria): make an abstract UserSettingsFactory that just includes the owner field


class BoxAccountFactory(ExternalAccountFactory):
    provider = 'box'
    prodiver_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n: 'secret-{0}'.format(n))
    expires_at = datetime.now() + relativedelta(seconds=3600)


class BoxUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = BoxUserSettings

    owner = SubFactory(UserFactory)


class BoxNodeSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = BoxNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(BoxUserSettingsFactory)
    with mock.patch('website.addons.box.model.BoxNodeSettings.fetch_folder_name') as mock_folder:
        mock_folder.return_value = 'Camera Uploads'


class BoxFileFactory(ModularOdmFactory):
    FACTORY_FOR = BoxFile

    node = SubFactory(ProjectFactory)
    path = 'foo.txt'

    @post_generation
    def add_box_addon(self, created, extracted):
        self.node.add_addon('box', auth=Auth(user=self.node.creator))
        self.node.save()
