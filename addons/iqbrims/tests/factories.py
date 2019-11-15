# -*- coding: utf-8 -*-
"""Factory boy factories for the IQB-RIMS addon."""
import factory

from django.utils import timezone
from dateutil.relativedelta import relativedelta

from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.iqbrims.models import NodeSettings
from addons.iqbrims.models import UserSettings


class IQBRIMSAccountFactory(ExternalAccountFactory):
    provider = 'iqbrims'
    provider_id = factory.Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = factory.Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = factory.Sequence(lambda n: 'secret-{0}'.format(n))
    expires_at = timezone.now() + relativedelta(days=1)

class IQBRIMSUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)

class IQBRIMSNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(IQBRIMSUserSettingsFactory)
    folder_id = '1234567890'
    folder_path = 'Drive/Camera Uploads'
