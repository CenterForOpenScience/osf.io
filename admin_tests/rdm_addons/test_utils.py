# -*- coding: utf-8 -*-

from nose import tools as nt

from tests.base import AdminTestCase
from osf_tests.factories import InstitutionFactory

from admin.rdm_addons import utils

import logging
logging.getLogger('website.project.model').setLevel(logging.DEBUG)

class TestRdmAddonOption(AdminTestCase):
    def setUp(self):
        super(TestRdmAddonOption, self).setUp()
        self.institution = InstitutionFactory()

    def tearDown(self):
        super(TestRdmAddonOption, self).tearDown()
        self.institution.delete()

    def test_get_rdm_addon_option_without_create_option(self):
        nt.assert_equal(None, utils.get_rdm_addon_option(self.institution.id, 's3', create=False))
        nt.assert_equal(None, utils.get_rdm_addon_option(self.institution.id, 'dropboxbusiness', create=False))

    def test_get_is_allowed_default(self):
        # newly created option
        option = utils.get_rdm_addon_option(self.institution.id, 's3')
        nt.assert_true(option.is_allowed)

        option = utils.get_rdm_addon_option(self.institution.id, 'dropboxbusiness')
        nt.assert_false(option.is_allowed)

        # option retrieved from database
        option = utils.get_rdm_addon_option(self.institution.id, 's3', create=False)
        nt.assert_true(option.is_allowed)

        option = utils.get_rdm_addon_option(self.institution.id, 'dropboxbusiness', create=False)
        nt.assert_false(option.is_allowed)
