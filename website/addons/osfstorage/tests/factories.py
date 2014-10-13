# -*- coding: utf-8 -*-

from factory import SubFactory

from tests.factories import ModularOdmFactory, AuthUserFactory

from website.addons.osfstorage import model


generic_location = {
    'service': 'cloud',
    'container': 'container',
    'object': '1615307',
}


class FileVersionFactory(ModularOdmFactory):
    FACTORY_FOR = model.FileVersion

    creator = SubFactory(AuthUserFactory)
    status = model.status['COMPLETE']
    location = generic_location

