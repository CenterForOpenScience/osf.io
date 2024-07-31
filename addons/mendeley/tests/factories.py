from django.utils import timezone
from factory import SubFactory, Sequence

from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from dateutil.relativedelta import relativedelta

from addons.mendeley import models


class MendeleyAccountFactory(ExternalAccountFactory):
    provider = 'mendeley'
    provider_id = Sequence(lambda n: f'id-{n}')
    oauth_key = Sequence(lambda n: f'key-{n}')
    oauth_secret = Sequence(lambda n: f'secret-{n}')
    expires_at = timezone.now() + relativedelta(days=1)


class MendeleyUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = models.UserSettings

    owner = SubFactory(UserFactory)


class MendeleyNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = models.NodeSettings

    owner = SubFactory(ProjectFactory)
