# -*- coding: utf-8 -*-
"""Factory boy factories for the Box addon."""

from framework.auth import Auth

from factory import SubFactory, Sequence, post_generation
from tests.factories import ModularOdmFactory, UserFactory, ProjectFactory

from website.addons.box.model import (
    BoxUserSettings, BoxNodeSettings, BoxFile
)

# TODO(sloria): make an abstract UserSettingsFactory that just includes the owner field
class BoxUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = BoxUserSettings

    owner = SubFactory(UserFactory)
    access_token = Sequence(lambda n: 'abcdef{0}'.format(n))


class BoxNodeSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = BoxNodeSettings

    owner = SubFactory(ProjectFactory)
    user_settings = SubFactory(BoxUserSettingsFactory)
    folder = 'Camera Uploads'


class BoxFileFactory(ModularOdmFactory):
    FACTORY_FOR = BoxFile

    node = SubFactory(ProjectFactory)
    path = 'foo.txt'

    @post_generation
    def add_box_addon(self, created, extracted):
        self.node.add_addon('box', auth=Auth(user=self.node.creator))
        self.node.save()
