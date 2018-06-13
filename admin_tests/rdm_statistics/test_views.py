# -*- coding: utf-8 -*-

from nose import tools as nt
from django.test import RequestFactory
#from django.contrib.auth.models import Permission
#from django.core.exceptions import PermissionDenied
#from django.http import HttpResponse, Http404

from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)
from admin_tests.utilities import setup_user_view
from admin_tests.rdm_statistics import factories as rdm_statistics_factories

#from osf.models.rdm_statistics import RdmStatistics
from osf.models.user import Institution

from admin.rdm_statistics import views
#from admin.rdm.utils import MAGIC_INSTITUTION_ID


class TestInstitutionListViewStat(AdminTestCase):
    """test InstitutionListViewStat"""
    def setUp(self):
        super(TestInstitutionListViewStat, self).setUp()
        self.user = AuthUserFactory()
        self.institutions = [InstitutionFactory(), InstitutionFactory()]
        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution1)
        self.request = RequestFactory().get('/fake_path')
        self.view = views.InstitutionListViewStat()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def tearDown(self):
        super(TestInstitutionListViewStat, self).tearDown()
        self.user.affiliated_institutions.remove(self.institution1)
        self.user.remove()
        for institution in self.institutions:
            institution.remove()

    def test_super_admin_login(self, *args, **kwargs):
        """統合管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """機関管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """統合管理者でも機関管理者でもないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """有効ではないユーザのログインテスト"""
        self.request.user.is_active = False
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """登録済みではないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = False
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_super_admin_get(self, *args, **kwargs):
        """統合管理者のgetメソッドのテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_admin_get(self, *args, **kwargs):
        """機関管理者のgetメソッドのテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.request.user.affiliated_institutions.add(self.institution1)
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 302)


class TestclassStatisticsView(AdminTestCase):
    """test StatisticsView"""
    def setUp(self):
        super(TestclassStatisticsView, self).setUp()
        self.user = AuthUserFactory()
        self.institution1 = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution1)
        self.request = RequestFactory().get('/fake_path')
        self.view = views.StatisticsView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.institution1.id}

    def tearDown(self):
        super(TestclassStatisticsView, self).tearDown()
        self.user.affiliated_institutions.remove(self.institution1)
        self.user.remove()
        self.institution1.remove()

    def test_super_admin_login(self):
        """統合管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """機関管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """統合管理者でも機関管理者でもないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """有効ではないユーザのログインテスト"""
        self.request.user.is_active = False
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """登録済みではないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = False
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """所属していない機関のユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': self.institution1.id + 1}
        nt.assert_equal(self.view.test_func(), False)
        self.view.kwargs = {'institution_id': self.institution1.id}

    def test_get_context_data(self, **kwargs):
        """contextのテスト"""
        ctx = self.view.get_context_data(**self.view.kwargs)
        nt.assert_is_instance(ctx['institution'], Institution)
        nt.assert_equal(ctx['institution'].id, self.institution1.id)
        nt.assert_true('current_date' in ctx)
        nt.assert_true('user' in ctx)
        nt.assert_true('provider_data_array' in ctx)
        nt.assert_true('token' in ctx)

class TestImageView(AdminTestCase):
    """test ImageView"""
    def setUp(self):
        super(TestImageView, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.institution1 = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution1)
        self.rdm_statistics = rdm_statistics_factories.RdmStatisticsFactory.create(institution=self.institution1, provider='s3', owner=self.user)
        self.rdm_statistics.save()
        self.view = views.ImageView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'graph_type': 'ext'}
        self.view.kwargs = {'provider': 's3'}
        self.view.kwargs = {'institution_id': self.institution1.id}

    def tearDown(self):
        super(TestImageView, self).tearDown()
        self.user.affiliated_institutions.remove(self.institution1)
        self.user.remove()
        self.institution1.remove()
        self.rdm_statistics.remove()

    def test_super_admin_login(self):
        """統合管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """機関管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """統合管理者でも機関管理者でもないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """有効ではないユーザのログインテスト"""
        self.request.user.is_active = False
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """登録済みではないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = False
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """所属していない機関のユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': self.institution1.id + 1}
        nt.assert_equal(self.view.test_func(), False)
        self.view.kwargs = {'institution_id': self.institution1.id}

    # def test_valid_get(self, *args, **kwargs):
    #     """有効なgetテスト"""
    #     res = self.view.get(self.request, *args, **self.view.kwargs)
    #     nt.assert_equal(res.status_code, 200)


class TestSendView(AdminTestCase):
    """test SendView"""
    def setUp(self):
        super(TestSendView, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.user = AuthUserFactory()
        self.institution1 = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution1)
        self.view = views.SendView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.institution1.id}

    def tearDown(self):
        super(TestSendView, self).tearDown()
        self.user.affiliated_institutions.remove(self.institution1)
        self.user.remove()
        self.institution1.remove()

    def test_super_admin_login(self):
        """統合管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """機関管理者のログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """統合管理者でも機関管理者でもないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """有効ではないユーザのログインテスト"""
        self.request.user.is_active = False
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """登録済みではないユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = False
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """所属していない機関のユーザのログインテスト"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': self.institution1.id + 1}
        nt.assert_equal(self.view.test_func(), False)
        self.view.kwargs = {'institution_id': self.institution1.id}

    def test_valid_get(self, *args, **kwargs):
        """有効なgetテスト"""
        res = self.view.get(self.request, *args, **self.view.kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_invalid_get(self, *args, **kwargs):
        """無効なgetテスト"""
        self.view.kwargs = {'institution_id': 100}
        res = self.view.get(self.request, *args, **self.view.kwargs)
        nt.assert_equal(res.status_code, 200)


class TestCreateCSV(AdminTestCase):
    """test ImageView"""
    def setUp(self):
        super(TestCreateCSV, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.institution1 = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution1)
        self.kwargs = {'institution_id': self.institution1.id}
        self.rdm_statistics = rdm_statistics_factories.RdmStatisticsFactory.create(institution=self.institution1, provider='s3', owaner=self.user)
        self.rdm_statistics.save()

    def tearDown(self):
        super(TestCreateCSV, self).tearDown()
        self.user.affiliated_institutions.remove(self.institution1)
        self.user.remove()
        self.institution1.remove()


# class TestGatherView(AdminTestCase):
#     """test ImageView"""
#     def setUp(self):
#         super(TestGatherView, self).setUp()

#     def tearDown(self):
#         super(TestGatherView, self).tearDown()
