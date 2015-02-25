# -*- coding: utf-8 -*-

from factory import SubFactory, Sequence

from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

import datetime

from dateutil.relativedelta import relativedelta

from website.addons.mendeley import model


class MendeleyAccountFactory(ExternalAccountFactory):
    provider = 'mendeley'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n: 'secret-{0}'.format(n))
    expires_at = datetime.datetime.now() + relativedelta(days=1)


class MendeleyUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = model.MendeleyUserSettings

    owner = SubFactory(UserFactory)


class MendeleyNodeSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = model.MendeleyNodeSettings

    owner = SubFactory(ProjectFactory)
