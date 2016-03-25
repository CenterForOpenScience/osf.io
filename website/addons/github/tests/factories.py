# -*- coding: utf-8 -*-

from factory import Sequence, SubFactory
from tests.factories import ExternalAccountFactory, ModularOdmFactory, ProjectFactory, UserFactory

from website.addons.github.model import GitHubNodeSettings, GitHubUserSettings


class GitHubAccountFactory(ExternalAccountFactory):
    provider = 'github'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    display_name = 'abc'

class GitHubUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = GitHubUserSettings

    owner = SubFactory(UserFactory)

class GitHubNodeSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = GitHubNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(GitHubUserSettingsFactory)
    repo = 'mock'
    user = 'abc'
