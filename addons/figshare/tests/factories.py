# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from django.utils import timezone
import factory
from factory.django import DjangoModelFactory

from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.figshare.models import UserSettings, NodeSettings

class FigshareAccountFactory(ExternalAccountFactory):
    provider = 'figshare'
    provider_id = factory.Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = factory.Sequence(lambda n: 'key-{0}'.format(n))
    expires_at = timezone.now() + relativedelta(seconds=3600)


class FigshareUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)


class FigshareNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
    user_settings = factory.SubFactory(FigshareUserSettingsFactory)
