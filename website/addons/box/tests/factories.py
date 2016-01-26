# -*- coding: utf-8 -*-
"""Factory boy factories for the Box addon."""
import mock
from datetime import datetime
from dateutil.relativedelta import relativedelta

from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

from website.addons.box.model import (
    BoxUserSettings,
    BoxNodeSettings
)

class BoxAccountFactory(ExternalAccountFactory):
    provider = 'box'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
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
