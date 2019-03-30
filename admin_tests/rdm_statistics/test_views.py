# -*- coding: utf-8 -*-

from nose import tools as nt
from django.test import RequestFactory

from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)
from admin_tests.utilities import setup_user_view
from admin_tests.rdm_statistics import factories as rdm_statistics_factories

from osf.models.user import Institution

from admin.rdm_statistics import views
from unittest import TestCase 
from mock import patch


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
        self.user.delete()
        for institution in self.institutions:
            institution.delete()

    def test_super_admin_login(self, *args, **kwargs):
        """test superuser login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """test institution administrator login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """test user not superuser or institution administrator login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """test invalid user login"""
        self.request.user.is_active = False
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """test unregistered user login"""
        self.request.user.is_active = True
        self.request.user.is_registered = False
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_super_admin_get(self, *args, **kwargs):
        """test superuser GET method"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_admin_get(self, *args, **kwargs):
        """test institution administrator GET method"""
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
        self.user.delete()
        self.institution1.delete()

    def test_super_admin_login(self):
        """test superuser login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """test institution administrator login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """test user not superuser or institution administrator login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """test invalid user login"""
        self.request.user.is_active = False
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """test unregistered user login"""
        self.request.user.is_active = True
        self.request.user.is_registered = False
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """test user unaffiliated institution login"""
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
        self.user.delete()
        self.institution1.delete()
        self.rdm_statistics.delete()

    def test_super_admin_login(self):
        """test superuser login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """test institution administrator login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """test user not superuser or institution administrator login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """test invalid user login"""
        self.request.user.is_active = False
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """test unregistered user login"""
        self.request.user.is_active = True
        self.request.user.is_registered = False
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """test user unaffiliated institution login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': self.institution1.id + 1}
        nt.assert_equal(self.view.test_func(), False)
        self.view.kwargs = {'institution_id': self.institution1.id}

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
        self.user.delete()
        self.institution1.delete()

    def test_super_admin_login(self):
        """test superuser login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_true(self.view.test_func())

    def test_admin_login(self):
        """test institution administrator login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        nt.assert_true(self.view.test_func())

    def test_non_admin_login(self):
        """test user not superuser or institution administrator login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = False
        nt.assert_equal(self.view.test_func(), False)

    def test_non_active_user_login(self):
        """test invalid user login"""
        self.request.user.is_active = False
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_registered_user_login(self):
        """test unregistered user login"""
        self.request.user.is_active = True
        self.request.user.is_registered = False
        self.request.user.is_superuser = True
        self.request.user.is_staff = True
        nt.assert_equal(self.view.test_func(), False)

    def test_non_affiliated_institution_user_login(self):
        """test user unaffiliated institution login"""
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = False
        self.request.user.is_staff = True
        self.view.kwargs = {'institution_id': self.institution1.id + 1}
        nt.assert_equal(self.view.test_func(), False)
        self.view.kwargs = {'institution_id': self.institution1.id}

    def test_valid_get(self, *args, **kwargs):
        """test valid GET method"""
        res = self.view.get(self.request, *args, **self.view.kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_invalid_get(self, *args, **kwargs):
        """test invalid GET method"""
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
        self.user.delete()
        self.institution1.delete()       

def test_simple_auth():
    import hashlib
    access_key_hexa = '2a85563b2b0f7d3168199f475365f57da1d56e4bb2ce2b7044eb058ae5e287637e7c636a772682d92c8d6b1830b9a97c5a5dc3de7016c60bde4baa7cc3b38aeb'
    nt.assert_true(views.simple_auth(access_key_hexa))

class TestGatherView(AdminTestCase):
    def setUp(self):
        super(TestGatherView, self).setUp()
        self.user = AuthUserFactory()
        self.institutions = [InstitutionFactory(), InstitutionFactory()]
        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution1)
        self.request = RequestFactory().get('/admin/templates/')
        self.view = views.InstitutionListViewStat()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.institution1.id}

    def tearDown(self):
        super(TestGatherView, self).tearDown()
        self.user.affiliated_institutions.remove(self.institution1)
        self.user.delete()
        for institution in self.institutions:
            institution.delete()
    
    def test_send_stat_mail(self, *args, **kwargs):
        nt.assert_equal(views.send_stat_mail(self.request).status_code,200)

    def test_send_error_mail(self, *args, **kwargs):
        ret = ''
        try:
            0/0
        except Exception as err:
           ret = views.send_error_mail(err)
        nt.assert_equal(ret.status_code,200)
    
    def test_send_email(self):
        from osf.models import OSFUser
        to_list = [self.user.username]
        cc_list = list(OSFUser.objects.filter(is_superuser=True).values_list('username', flat=True))
        mail_data = {
            'subject': 'statistic information at  Random date' ,
            'content': 'statistic information of storage in ',
            'attach_file': 'XYZ',
            'attach_data': 'abc'
        }
        user = self.user
        nt.assert_equal(views.send_email(to_list=to_list, cc_list=cc_list, data=mail_data, user=user)['is_success'],False)

    @patch('admin.rdm_statistics.views.render_to_string',return_value='<h1>My First Heading</h1>', autospec=True)
    @patch('admin.rdm_statistics.views.pdfkit',return_value='41', autospec=True)
    def test_get_pdf_data(self,render_to_string,pdfkit):
        nt.assert_not_equal(views.get_pdf_data(institution=self.institutions[0]).return_value ,'41')

    @patch('admin.rdm_statistics.views.render_to_string')
    @patch('admin.rdm_statistics.views.pdfkit')
    def test_create_pdf(self,render_to_string,pdfkit):
        render_to_string.return_value = '<h1>My First Heading</h1>'
        pdfkit.return_value = '41'        
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_equal(views.create_pdf(self.request,True,**self.view.kwargs).status_code,200)

    def test_create_csv(self,**kwargs):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        nt.assert_equal(views.create_csv(self.request,**self.view.kwargs).status_code,200)