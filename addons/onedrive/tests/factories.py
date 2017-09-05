# -*- coding: utf-8 -*-
"""Factory boy factories for the OneDrive addon."""
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from factory import SubFactory, Sequence
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.onedrive.models import UserSettings, NodeSettings


class OneDriveAccountFactory(ExternalAccountFactory):
    provider = 'onedrive'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n: 'secret-{0}'.format(n))
    expires_at = timezone.now() + relativedelta(days=1)

class OneDriveUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = SubFactory(UserFactory)


class OneDriveNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(OneDriveUserSettingsFactory)
    folder_id = '1234567890'
    folder_path = 'Drive/Camera Uploads'
