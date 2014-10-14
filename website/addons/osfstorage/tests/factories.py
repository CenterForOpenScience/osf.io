# -*- coding: utf-8 -*-

from factory import SubFactory, post_generation

from tests.factories import ModularOdmFactory, AuthUserFactory

import datetime

from website.addons.osfstorage import model


generic_location = {
    'service': 'cloud',
    'container': 'container',
    'object': '1615307',
}


class FileVersionFactory(ModularOdmFactory):
    FACTORY_FOR = model.FileVersion

    creator = SubFactory(AuthUserFactory)
    date_modified = datetime.datetime.utcnow()
    status = model.status['COMPLETE']
    location = generic_location

    @post_generation
    def refresh(self, create, extracted, **kwargs):
        if not create:
            return
        self.reload()
