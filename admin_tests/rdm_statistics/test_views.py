# -*- coding: utf-8 -*-
from nose import tools as nt
from django.test import RequestFactory

from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ProjectFactory
)
from admin_tests.utilities import setup_user_view
from admin_tests.rdm_statistics import factories as rdm_statistics_factories

from osf.models.user import Institution

from admin.rdm_statistics import views
from mock import patch

import datetime
import tempfile
import os
import uuid
import shutil
import json
from osf.models import OSFUser


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
    access_key_hexa = '2a85563b2b0f7d3168199f475365f57da1d56e4bb2ce2b7044eb058ae5e287637e7c636a772682d92c8d6b1830b9a97c5a5dc3de7016c60bde4baa7cc3b38aeb'
    nt.assert_true(views.simple_auth(access_key_hexa))

def test_get_start_date():
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(weeks=(10))\
        + datetime.timedelta(days=(1))
    nt.assert_equal(views.get_start_date(end_date), start_date)

def create_test_file(node, user, filename='test_file', create_guid=True):
    from addons.osfstorage import settings as osfstorage_settings
    osfstorage = node.get_addon('osfstorage')
    root_node = osfstorage.get_root()
    test_file = root_node.append_file(filename)

    if create_guid:
        test_file.get_guid(create=True)

    test_file.create_version(user, {
        'object': '06d80e',
        'service': 'cloud',
        osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
    }, {
        'size': 1337,
        'contentType': 'img/png'
    }).save()
    return test_file

def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data
    return MockResponse({'data': [{'type': 'files', 'links': {'delete': 'http://localhost:7777/v1/resources/jy73h/providers/osfstorage/5ca01e2d3618060086091b85', 'upload': 'http://localhost:7777/v1/resources/jy73h/providers/osfstorage/5ca01e2d3618060086091b85?kind=file', 'move': 'http://localhost:7777/v1/resources/jy73h/providers/osfstorage/5ca01e2d3618060086091b85', 'download': 'http://localhost:7777/v1/resources/jy73h/providers/osfstorage/5ca01e2d3618060086091b85'}, 'id': 'osfstorage/5ca01e2d3618060086091b85', 'attributes': {'path': '/5ca01e2d3618060086091b85', 'size': 44167, 'contentType': None, 'created_utc': '2019-03-31T01:55:57.706150+00:00', 'provider': 'osfstorage', 'sizeInt': 44167, 'etag': '42811153669f5825fda6f810975bc44af5973bb7c3a1b163ae722358715673d0', 'modified_utc': '2019-03-31T01:55:57.706150+00:00', 'modified': '2019-03-31T01:55:57.70615+00:00', 'extra': {'latestVersionSeen': None, 'guid': None, 'version': 1, 'hashes': {'sha256': '93afecd63c60f0ff0ef6cf0e8b904c281f00f9e5251751b9fa292f16e6dc0d9b', 'md5': 'a89fa2dd3c6bbff0f5e58aa2b4e8f735'}, 'checkout': None, 'downloads': 0}, 'resource': 'jy73h', 'name': 'OSF contact.png', 'materialized': '/OSF contact.png', 'kind': 'file'}}]}, 200)

class TestGatherView(AdminTestCase):
    def setUp(self):
        super(TestGatherView, self).setUp()
        self.user = AuthUserFactory()
        self.institutions = [InstitutionFactory(), InstitutionFactory()]
        self.institution1 = InstitutionFactory()
        self.institution2 = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution1)
        self.project = ProjectFactory(creator=self.user, is_public=True)
        self.project.affiliated_institutions.add(self.institution1)
        self.project.save()
        self.file_node = create_test_file(node=self.project, user=self.user, filename='some_file.some_extension')
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_file = os.path.join(self.tmp_dir, self.file_node.name)
        with open(self.tmp_file, 'wb') as file:
            file.write(str(uuid.uuid4()).encode('utf-8'))
        self.request = RequestFactory().get('/fake_path')
        self.view = views.GatherView()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'institution_id': self.institution1.id, 'access_token': '2A85563B2B0F7D3168199F475365F57DA1D56E4BB2CE2B7044EB058AE5E287637E7C636A772682D92C8D6B1830B9A97C5A5DC3DE7016C60BDE4BAA7CC3B38AEB'.lower()}

    def tearDown(self):
        super(TestGatherView, self).tearDown()
        self.user.affiliated_institutions.remove(self.institution1)
        self.project.affiliated_institutions.remove(self.institution1)
        self.project.delete()
        self.user.delete()
        for institution in self.institutions:
            institution.delete()
        shutil.rmtree(self.tmp_dir)

    @patch('admin.rdm_statistics.views.requests.Session.get', side_effect=mocked_requests_get)
    def test_get(self, *args, **kwargs):
        resp = json.loads(self.view.get(self, self.request, self.view.args, self.view.kwargs).content)
        # metadata addon is now enabled by default, so we have 3 providers
        nt.assert_equal(len(resp), 3)

    def test_send_stat_mail(self, *args, **kwargs):
        nt.assert_equal(views.send_stat_mail(self.request).status_code, 200)

    def test_send_error_mail(self, *args, **kwargs):
        ret = views.send_error_mail(Exception())
        nt.assert_equal(ret.status_code, 200)

    def test_send_email(self):
        to_list = [self.user.username]
        cc_list = list(OSFUser.objects.filter(is_superuser=True).values_list('username', flat=True))
        mail_data = {
            'subject': 'statistic information at  Random date',
            'content': 'statistic information of storage in ',
            'attach_file': 'XYZ',
            'attach_data': 'abc'
        }
        nt.assert_equal(views.send_email(to_list=to_list, cc_list=cc_list, data=mail_data,)['is_success'], False)

    @patch('admin.rdm_statistics.views.render_to_string', return_value='<h1>My First Heading</h1>', autospec=True)
    @patch('admin.rdm_statistics.views.pdfkit', return_value='41', autospec=True)
    def test_get_pdf_data(self, render_to_string, pdfkit):
        nt.assert_not_equal(views.get_pdf_data(institution=self.institutions[0]).return_value, '41')

    @patch('admin.rdm_statistics.views.pdfkit')
    @patch('admin.rdm_statistics.views.render_to_string')
    def test_create_pdf(self, render_to_string, mock_pdfkit):
        render_to_string.return_value = '<h1>My First Heading</h1>'
        mock_pdfkit.from_string.return_value = '<h1>My First Heading</h1>'

        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        result = views.create_pdf(self.request, True, **self.view.kwargs)
        nt.assert_true(result.status_code, 200)
        nt.assert_true('.pdf' in result['Content-Disposition'].lower())

    def test_create_csv(self, **kwargs):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True
        result = views.create_csv(self.request, **self.view.kwargs)
        nt.assert_equal(result.status_code, 200)
        nt.assert_true('.csv' in result['Content-Disposition'].lower())

    def test_get_all_statistic_data_csv(self, **kwargs):
        nt.assert_is_instance(views.get_all_statistic_data_csv(self.institution1, **self.view.kwargs), type([]))

    @patch('admin.rdm_statistics.views.requests.Session.get', side_effect=mocked_requests_get)
    def test_get_graphs(self, mock_sessionget):
        self.request.user.is_active = True
        self.request.user.is_registered = True
        self.request.user.is_superuser = True

        # Runs the "cron" so the statistics data gets updated in the statistics view
        self.view.get(self, self.request, self.view.args, self.view.kwargs)

        result = views.ImageView.as_view()(
            self.request,
            institution_id=self.institution1.id,
            graph_type='num',
            provider='osfstorage'
        )
        nt.assert_equal(result['content-type'], 'image/png')

        result = views.ImageView.as_view()(
            self.request,
            institution_id=self.institution1.id,
            graph_type='size',
            provider='osfstorage'
        )
        nt.assert_equal(result['content-type'], 'image/png')

        result = views.ImageView.as_view()(
            self.request,
            institution_id=self.institution1.id,
            graph_type='ext',
            provider='osfstorage'
        )
        nt.assert_equal(result['content-type'], 'image/png')
