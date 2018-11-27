# -*- coding: utf-8 -*-

from nose import tools as nt
from django.test import RequestFactory

from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ExternalAccountFactory,
)


from admin_tests.utilities import setup_user_view
from admin.rdm_addons import views
from admin.rdm_addons import utils
from admin.rdm.utils import MAGIC_INSTITUTION_ID

from admin_tests.rdm_addons import factories as rdm_addon_factories

import logging
logging.getLogger('website.project.model').setLevel(logging.DEBUG)

class TestInstitutionListView(AdminTestCase):
    def setUp(self):
        super(TestInstitutionListView, self).setUp()
        self.user = AuthUserFactory()
        self.institutions = [InstitutionFactory(), InstitutionFactory()]
        self.request = RequestFactory().get('/fake_path')
        self.view = views.InstitutionListView()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def tearDown(self):
        super(TestInstitutionListView, self).tearDown()
        self.user.delete()
        for institution in self.institutions:
            institution.delete()

    def test_super_admin_login(self, *args, **kwargs):
        """test superuser login"""
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """test institution administrator login"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """test user not superuser or institution administrator login"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """test invalid user login"""
        self.request.user.is_active = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """test unregistered user login"""
        self.request.user.is_registered = False
        nt.assert_equal(self.view.test_func(), False)

    def test_super_admin_get(self, *args, **kwargs):
        """test superuser GET method"""
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_admin_get(self, *args, **kwargs):
        """test institution administrator GET method"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 302)


class TestAddonListView(AdminTestCase):
    def setUp(self):
        super(TestAddonListView, self).setUp()
        self.user = AuthUserFactory()
        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution1)

        self.request = RequestFactory().get('/fake_path')
        self.view = views.AddonListView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.institution1.id}

    def tearDown(self):
        super(TestAddonListView, self).tearDown()
        self.user.affiliated_institutions.remove(self.institution1)
        self.user.delete()
        self.institution1.delete()
        self.institution2.delete()

    def test_super_admin_login(self):
        """test superuser login"""
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """test institution administrator login"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """test user not superuser or institution administrator login"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """test invalid user login"""
        self.request.user.is_active = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """test unregistered user login"""
        self.request.user.is_registered = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """test user unaffiliated institution login"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': self.institution1.id + 1}
        nt.assert_equal(self.view.test_func(), False)


class TestIconView(AdminTestCase):
    def setUp(self):
        super(TestIconView, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.view = views.IconView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'addon_name': 's3'}

    def tearDown(self):
        super(TestIconView, self).tearDown()
        self.user.delete()

    def test_login_user(self):
        nt.assert_true(self.view.test_func())

    def test_valid_get(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **self.view.kwargs)
        nt.assert_equal(res.status_code, 200)


class TestAddonAllowView(AdminTestCase):
    def setUp(self):
        super(TestAddonAllowView, self).setUp()
        self.user = AuthUserFactory()
        self.institution1 = InstitutionFactory()
        self.external_account = ExternalAccountFactory()

        self.rdm_addon_option = rdm_addon_factories.RdmAddonOptionFactory()
        self.rdm_addon_option.external_accounts.add(self.external_account)
        self.rdm_addon_option.save()

        self.user.affiliated_institutions.add(self.rdm_addon_option.institution)
        self.user.external_accounts.add(self.external_account)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.AddonAllowView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {
            'addon_name': self.rdm_addon_option.provider,
            'institution_id': self.rdm_addon_option.institution.id,
            'allowed': '1',
        }

    def tearDown(self):
        super(TestAddonAllowView, self).tearDown()
        institution = self.rdm_addon_option.institution
        self.user.affiliated_institutions.remove(institution)
        if self.user.external_accounts.filter(pk=self.external_account.id).exists():
            self.user.external_accounts.remove(self.external_account)
        self.user.delete()
        self.institution1.delete()
        self.rdm_addon_option.external_accounts.remove(self.external_account)
        self.rdm_addon_option.delete()
        institution.delete()
        self.external_account.delete()

    def test_super_admin_login(self):
        """test superuser login"""
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """test institution administrator login"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """test user not superuser or institution administrator login"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """test invalid user login"""
        self.request.user.is_active = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """test unregistered user login"""
        self.request.user.is_registered = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """test user unaffiliated institution login"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': self.rdm_addon_option.institution.id + 1}
        nt.assert_equal(self.view.test_func(), False)

    def test_get(self, *args, **kwargs):
        self.view.get(self.request, *args, **self.view.kwargs)
        rdm_addon_option = utils.get_rdm_addon_option(self.rdm_addon_option.institution.id, self.view.kwargs['addon_name'])
        nt.assert_true(rdm_addon_option.is_allowed)
        nt.assert_equal(rdm_addon_option.provider, self.view.kwargs['addon_name'])
        nt.assert_equal(rdm_addon_option.institution_id, self.view.kwargs['institution_id'])

    def test_get_disallowed(self, *args, **kwargs):
        self.view.kwargs['allowed'] = False
        self.view.get(self.request, *args, **self.view.kwargs)
        rdm_addon_option = utils.get_rdm_addon_option(self.rdm_addon_option.institution.id, self.view.kwargs['addon_name'])
        nt.assert_equal(rdm_addon_option.is_allowed, False)
        nt.assert_equal(rdm_addon_option.provider, self.view.kwargs['addon_name'])
        nt.assert_equal(rdm_addon_option.institution_id, self.view.kwargs['institution_id'])
        nt.assert_equal(self.user.external_accounts.filter(pk=self.external_account.id).exists(), False)

class TestNoInstitutionAddonAllowView(AdminTestCase):
    def setUp(self):
        super(TestNoInstitutionAddonAllowView, self).setUp()
        self.user = AuthUserFactory()
        self.external_account = ExternalAccountFactory()

        self.rdm_addon_option = rdm_addon_factories.RdmAddonNoInstitutionFactoryOption()
        self.rdm_addon_option.external_accounts.add(self.external_account)
        self.rdm_addon_option.save()

        self.user.external_accounts.add(self.external_account)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.AddonAllowView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {
            'addon_name': self.rdm_addon_option.provider,
            'institution_id': MAGIC_INSTITUTION_ID,
            'allowed': '1',
        }

    def tearDown(self):
        super(TestNoInstitutionAddonAllowView, self).tearDown()
        if self.user.external_accounts.filter(pk=self.external_account.id).exists():
            self.user.external_accounts.remove(self.external_account)
        self.user.delete()
        self.rdm_addon_option.external_accounts.remove(self.external_account)
        self.rdm_addon_option.delete()
        self.external_account.delete()

    def test_super_admin_login(self):
        """test superuser login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_get(self, *args, **kwargs):
        rdm_addon_option = utils.get_rdm_addon_option(MAGIC_INSTITUTION_ID, self.view.kwargs['addon_name'])
        nt.assert_true(rdm_addon_option.is_allowed)
        nt.assert_equal(rdm_addon_option.provider, self.view.kwargs['addon_name'])

    def test_get_disallowed(self, *args, **kwargs):
        self.view.kwargs['allowed'] = False
        self.view.get(self.request, *args, **self.view.kwargs)
        rdm_addon_option = utils.get_rdm_addon_option(MAGIC_INSTITUTION_ID, self.view.kwargs['addon_name'])
        nt.assert_equal(rdm_addon_option.is_allowed, False)
        nt.assert_equal(rdm_addon_option.provider, self.view.kwargs['addon_name'])
        nt.assert_equal(self.user.external_accounts.filter(pk=self.external_account.id).exists(), False)

class TestAddonForceView(AdminTestCase):
    def setUp(self):
        super(TestAddonForceView, self).setUp()
        self.user = AuthUserFactory()
        self.external_account = ExternalAccountFactory()

        self.rdm_addon_option = rdm_addon_factories.RdmAddonOptionFactory()
        self.rdm_addon_option.external_accounts.add(self.external_account)
        self.rdm_addon_option.save()

        self.user.affiliated_institutions.add(self.rdm_addon_option.institution)
        self.user.external_accounts.add(self.external_account)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.AddonForceView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {
            'addon_name': self.rdm_addon_option.provider,
            'institution_id': self.rdm_addon_option.institution.id,
            'forced': '1',
        }

    def tearDown(self):
        super(TestAddonForceView, self).tearDown()
        institution = self.rdm_addon_option.institution
        self.user.affiliated_institutions.remove(institution)
        if self.user.external_accounts.filter(pk=self.external_account.id).exists():
            self.user.external_accounts.remove(self.external_account)
        self.user.delete()
        self.rdm_addon_option.external_accounts.remove(self.external_account)
        self.rdm_addon_option.delete()
        institution.delete()
        self.external_account.delete()

    def test_super_admin_login(self):
        """test superuser login"""
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """test institution administrator login"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """test user not superuser or institution administrator login"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """test invalid user login"""
        self.request.user.is_active = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """test unregistered user login"""
        self.request.user.is_registered = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """test user unaffiliated institution login"""
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': self.rdm_addon_option.institution.id + 1}
        nt.assert_equal(self.view.test_func(), False)

    def test_get(self, *args, **kwargs):
        self.view.get(self.request, *args, **self.view.kwargs)
        rdm_addon_option = utils.get_rdm_addon_option(self.rdm_addon_option.institution.id, self.view.kwargs['addon_name'])
        nt.assert_true(rdm_addon_option.is_forced)
        nt.assert_equal(rdm_addon_option.provider, self.view.kwargs['addon_name'])

    def test_get_not_forced(self, *args, **kwargs):
        self.view.kwargs['forced'] = False
        self.view.get(self.request, *args, **self.view.kwargs)
        rdm_addon_option = utils.get_rdm_addon_option(self.rdm_addon_option.institution.id, self.view.kwargs['addon_name'])
        nt.assert_equal(rdm_addon_option.is_forced, False)
        nt.assert_equal(rdm_addon_option.provider, self.view.kwargs['addon_name'])
        nt.assert_true(self.user.external_accounts.filter(pk=self.external_account.id).exists())


class TestNoInstitutionAddonForceView(AdminTestCase):
    def setUp(self):
        super(TestNoInstitutionAddonForceView, self).setUp()
        self.user = AuthUserFactory()
        self.external_account = ExternalAccountFactory()

        self.rdm_addon_option = rdm_addon_factories.RdmAddonNoInstitutionFactoryOption()
        self.rdm_addon_option.external_accounts.add(self.external_account)
        self.rdm_addon_option.save()

        self.user.external_accounts.add(self.external_account)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.AddonForceView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {
            'addon_name': self.rdm_addon_option.provider,
            'institution_id': MAGIC_INSTITUTION_ID,
            'forced': '1',
        }

    def tearDown(self):
        super(TestNoInstitutionAddonForceView, self).tearDown()
        if self.user.external_accounts.filter(pk=self.external_account.id).exists():
            self.user.external_accounts.remove(self.external_account)
        self.user.delete()
        self.rdm_addon_option.external_accounts.remove(self.external_account)
        self.rdm_addon_option.delete()
        self.external_account.delete()

    def test_get(self, *args, **kwargs):
        self.view.get(self.request, *args, **self.view.kwargs)
        rdm_addon_option = utils.get_rdm_addon_option(MAGIC_INSTITUTION_ID, self.view.kwargs['addon_name'])
        logging.debug(rdm_addon_option)
        nt.assert_true(rdm_addon_option.is_forced)
        nt.assert_equal(rdm_addon_option.provider, self.view.kwargs['addon_name'])

    def test_get_not_forced(self, *args, **kwargs):
        self.view.kwargs['forced'] = False
        self.view.get(self.request, *args, **self.view.kwargs)
        rdm_addon_option = utils.get_rdm_addon_option(MAGIC_INSTITUTION_ID, self.view.kwargs['addon_name'])
        nt.assert_equal(rdm_addon_option.is_forced, False)
        nt.assert_equal(rdm_addon_option.provider, self.view.kwargs['addon_name'])
