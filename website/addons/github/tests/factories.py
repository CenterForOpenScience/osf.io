# -*- coding: utf-8 -*-

from tests.factories import ModularOdmFactory, FakerAttribute

from website.addons.github import model

class GitHubOauthSettingsFactory(ModularOdmFactory):

    FACTORY_FOR = model.AddonGitHubOauthSettings

    oauth_access_token = FakerAttribute('md5')
    oauth_token_type = None
    github_user_id = FakerAttribute('sha1')
    github_user_name = FakerAttribute('domain_word')
