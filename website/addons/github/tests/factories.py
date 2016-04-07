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
    class Meta:
        model = GitHubUserSettings

    owner = SubFactory(UserFactory)


class GitHubNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = GitHubNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(GitHubUserSettingsFactory)
    repo = 'mock'
    user = 'abc'
