# -*- coding: utf-8 -*-
"""Factory boy factories for the Dropbox addon."""

from factory import SubFactory, Sequence
from tests.factories import ModularOdmFactory, UserFactory

from website.addons.dropbox.model import DropboxUserSettings

# TODO(sloria): make an abstract UserSettingsFactory that just includes the owner field
class DropboxUserSettingsFactory(ModularOdmFactory):
    FACTORY_FOR = DropboxUserSettings

    owner = SubFactory(UserFactory)
    access_token = Sequence(lambda n: 'abcdef{0}'.format(n))
