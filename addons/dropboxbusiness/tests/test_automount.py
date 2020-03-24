import unittest

from mock import patch, Mock
import pytest
from nose.tools import *  # noqa (PEP8 asserts)

from admin.rdm_addons.utils import get_rdm_addon_option

from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    InstitutionFactory,
    ExternalAccountFactory,
    UserFactory,
    ProjectFactory
)
from addons.dropboxbusiness.models import NodeSettings
from admin_tests.rdm_addons import factories as rdm_addon_factories

pytestmark = pytest.mark.django_db

class DropboxBusinessAccountFactory(ExternalAccountFactory):
    provider = 'dropboxbusiness'

FILEACCESS_NAME = 'dropboxbusiness'
MANAGEMENT_NAME = 'dropboxbusiness_manage'
DBXBIZ = 'addons.dropboxbusiness'

class TestDropboxBusiness(unittest.TestCase):

    def setUp(self):

        super(TestDropboxBusiness, self).setUp()

        self.institution = InstitutionFactory()

        self.user = UserFactory()
        self.user.eppn = fake_email()
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.f_option = get_rdm_addon_option(self.institution.id,
                                             FILEACCESS_NAME)
        self.m_option = get_rdm_addon_option(self.institution.id,
                                             MANAGEMENT_NAME)

        f_account = ExternalAccountFactory(provider=FILEACCESS_NAME)
        m_account = ExternalAccountFactory(provider=MANAGEMENT_NAME)

        self.f_option.external_accounts.add(f_account)
        self.m_option.external_accounts.add(m_account)

    def _new_project(self):
        with patch(DBXBIZ + '.utils.TeamInfo') as mock1, \
             patch(DBXBIZ + '.utils.get_current_admin_group_and_sync') as mock2, \
             patch(DBXBIZ + '.utils.get_current_admin_dbmid') as mock3, \
             patch(DBXBIZ + '.utils.create_team_folder') as mock4:
            mock2.return_value = (Mock(), Mock())
            mock3.return_value = 'dbmid:dummy'
            mock4.return_value = ('dbtid:dummy', 'g:dummy')
            self.project = ProjectFactory(creator=self.user)

    def _allowed(self):
        self.f_option.is_allowed = True
        self.f_option.save()

    def test_dropboxbusiness_default_is_not_allowed(self):
        assert_false(self.f_option.is_allowed)
        self._new_project()
        result = self.project.get_addon('dropboxbusiness')
        assert_equal(result, None)

    def test_dropboxbusiness_no_eppn(self):
        self.user.eppn = None
        self.user.save()
        self._allowed()
        self._new_project()
        result = self.project.get_addon('dropboxbusiness')
        assert_equal(result, None)

    def test_dropboxbusiness_no_institution(self):
        self.user.affiliated_institutions.clear()
        self._allowed()
        self._new_project()
        result = self.project.get_addon('dropboxbusiness')
        assert_equal(result, None)

    def test_dropboxbusiness_no_addon_option(self):
        self.f_option.delete()
        self._allowed()
        self._new_project()
        result = self.project.get_addon('dropboxbusiness')
        assert_equal(result, None)

    def test_dropboxbusiness_automount(self):
        self.f_option.is_allowed = True
        self.f_option.save()
        self._new_project()
        result = self.project.get_addon('dropboxbusiness')
        assert_true(isinstance(result, NodeSettings))
        assert_equal(result.admin_dbmid, 'dbmid:dummy')
        assert_equal(result.team_folder_id, 'dbtid:dummy')
        assert_equal(result.group_id, 'g:dummy')


