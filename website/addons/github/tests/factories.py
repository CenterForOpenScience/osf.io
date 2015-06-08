# -*- coding: utf-8 -*-

from factory import SubFactory, Sequence

from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory, ExternalAccountFactory

import datetime

from dateutil.relativedelta import relativedelta

from website.addons.github import model


class GitHubAccountFactory(ExternalAccountFactory):
    provider = 'github'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    oauth_secret = Sequence(lambda n: 'secret-{0}'.format(n))
    expires_at = datetime.datetime.now() + relativedelta(days=1)


class GitHubUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = model.GitHubUserSettings

    owner = SubFactory(UserFactory)


class GitHubNodeSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = model.GitHubNodeSettings

    owner = SubFactory(ProjectFactory)
