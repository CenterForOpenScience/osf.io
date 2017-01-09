# -*- coding: utf-8 -*-
from django.utils import timezone
from factory import SubFactory, Sequence

from factory.django import DjangoModelFactory
from tests.factories import UserFactory, ProjectFactory, ExternalAccountFactory

from dateutil.relativedelta import relativedelta

from addons.zotero import models


class ZoteroAccountFactory(ExternalAccountFactory):
    provider = 'zotero'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    provider_name = 'Fake Provider'
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n: 'secret-{0}'.format(n))
    expires_at = timezone.now() + relativedelta(days=1)


class ZoteroUserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = models.UserSettings

    owner = SubFactory(UserFactory)


class ZoteroNodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = models.NodeSettings

    owner = SubFactory(ProjectFactory)
