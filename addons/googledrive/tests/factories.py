# -*- coding: utf-8 -*-
"""Factory boy factories for the Google Drive addon."""
import factory

from django.utils import timezone
from dateutil.relativedelta import relativedelta

from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.googledrive.models import NodeSettings
from addons.googledrive.models import UserSettings


class GoogleDriveAccountFactory(ExternalAccountFactory):
    provider = 'googledrive'
    provider_id = factory.Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = factory.Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = factory.Sequence(lambda n: 'secret-{0}'.format(n))
    expires_at = timezone.now() + relativedelta(days=1)

class GoogleDriveUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)

class GoogleDriveNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(GoogleDriveUserSettingsFactory)
    folder_id = '1234567890'
    folder_path = 'Drive/Camera Uploads'
