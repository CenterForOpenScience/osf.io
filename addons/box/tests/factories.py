"""Factory boy factories for the Box addon."""
from datetime import datetime
from dateutil.relativedelta import relativedelta
from django.utils import timezone

from factory import SubFactory, Sequence
from factory.django import DjangoModelFactory

from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from addons.box.models import NodeSettings
from addons.box.models import UserSettings


class BoxAccountFactory(ExternalAccountFactory):
    provider = 'box'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    expires_at = timezone.now() + relativedelta(seconds=3600)


class BoxUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = SubFactory(UserFactory)


class BoxNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(BoxUserSettingsFactory)
