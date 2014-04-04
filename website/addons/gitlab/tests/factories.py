# -*- coding: utf-8 -*-
"""Factory boy factories for the Dropbox addon."""

from factory import SubFactory
from tests.factories import ModularOdmFactory, ProjectFactory

from website.addons.gitlab.model import GitlabGuidFile


class GitlabGuidFileFactory(ModularOdmFactory):

    FACTORY_FOR = GitlabGuidFile

    node = SubFactory(ProjectFactory)
    path = 'foo.txt'
