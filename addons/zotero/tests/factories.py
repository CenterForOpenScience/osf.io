from django.utils import timezone
from factory import SubFactory, Sequence

from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from dateutil.relativedelta import relativedelta

from addons.zotero import models


class ZoteroAccountFactory(ExternalAccountFactory):
    provider = 'zotero'
    provider_id = Sequence(lambda n: f'id-{n}')
    provider_name = 'Fake Provider'
    oauth_key = Sequence(lambda n: f'key-{n}')
    oauth_secret = Sequence(lambda n: f'secret-{n}')
    expires_at = timezone.now() + relativedelta(days=1)


class ZoteroUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = models.UserSettings

    owner = SubFactory(UserFactory)


class ZoteroNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = models.NodeSettings

    owner = SubFactory(ProjectFactory)
