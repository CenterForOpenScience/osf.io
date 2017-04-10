# -*- coding: utf-8 -*-

from factory import Sequence, SubFactory
from tests.factories import ExternalAccountFactory, ModularOdmFactory, ProjectFactory, UserFactory

from website.addons.gitlab.model import GitLabNodeSettings, GitLabUserSettings


class GitLabAccountFactory(ExternalAccountFactory):
    provider = 'gitlab'
    provider_id = Sequence(lambda n: 'id-{0}'.format(n))
    oauth_key = Sequence(lambda n: 'key-{0}'.format(n))
    display_name = 'abc'


class GitLabUserSettingsFactory(ModularOdmFactory):
    class Meta:
        model = GitLabUserSettings

    owner = SubFactory(UserFactory)


class GitLabNodeSettingsFactory(ModularOdmFactory):
    class Meta:
        model = GitLabNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(GitLabUserSettingsFactory)
