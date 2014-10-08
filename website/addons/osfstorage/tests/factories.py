# -*- coding: utf-8 -*-

from tests.factories import ModularOdmFactory

from website.addons.osfstorage import model


generic_location = {
    'service': 'cloud',
    'container': 'container',
    'object': '1615307',
}


class FileVersionFactory(ModularOdmFactory):
    FACTORY_FOR = model.FileVersion

    status = model.status['COMPLETE']
    location = generic_location

