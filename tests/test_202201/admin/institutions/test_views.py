import json
from operator import itemgetter
from nose import tools as nt
import mock
import pytest
from django.test import RequestFactory
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied

from api.base import settings as api_settings
from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    ProjectFactory,
    RegionFactory
)
from osf.models import Institution, Node, UserQuota
from admin_tests.utilities import setup_form_view, setup_user_view, setup_view
from admin.institutions import views
from admin.institutions.forms import InstitutionForm
from admin.base.forms import ImportFileForm
from django.urls import reverse


@pytest.mark.skip('Clone test case from tests/test_quota.py for making coverage')
class TestUserListByInstitutionID(AdminTestCase):

    def setUp(self):
        super(TestUserListByInstitutionID, self).setUp()
        self.user = AuthUserFactory(fullname='Alex fullname')
        self.user2 = AuthUserFactory(fullname='Kenny Dang')
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user2.affiliated_institutions.add(self.institution)
        self.user.save()
        self.user2.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = views.UserListByInstitutionID()
        self.view = setup_view(self.view,
                               self.request,
                               institution_id=self.institution.id)

    def test_default_user_list_by_institution_id(self, *args, **kwargs):

        res = self.view.get_userlist()
        nt.assert_is_instance(res, list)

    def test_search_email_by_institution_id(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'email': self.user2.username
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(res[0]['username'], self.user2.username)
        nt.assert_equal(len(res), 1)

    def test_search_guid_by_institution_id(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'guid': self.user2._id
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(res[0]['id'], self.user2._id)
        nt.assert_equal(len(res), 1)

    def test_search_name_by_institution_id(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'info': 'kenny'
            }
        )
        request.user = self.user

        view = views.UserListByInstitutionID()
        view = setup_view(view, request, institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(len(res), 1)
        nt.assert_in(res[0]['fullname'], self.user2.fullname)

    def test_search_name_guid_email_inputted(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'email': 'test@gmail.com',
                'guid': self.user._id,
                'info': 'kenny'
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(res[0]['id'], self.user._id)
        nt.assert_in(res[0]['fullname'], self.user.fullname)
        nt.assert_equal(len(res), 1)

    def test_search_not_found(self):
        request = RequestFactory().get(
            reverse('institutions:institution_user_list',
                    kwargs={'institution_id': self.institution.id}),
            {
                'email': 'sstest@gmail.com',
                'guid': 'guid2',
                'info': 'guid2'
            }
        )
        request.user = self.user
        view = views.UserListByInstitutionID()
        view = setup_view(view, request,
                          institution_id=self.institution.id)
        res = view.get_userlist()

        nt.assert_equal(len(res), 0)

@pytest.mark.skip('Clone test case from tests/test_quota.py for making coverage')
class TestExportFileTSV(AdminTestCase):
    def setUp(self):
        super(TestExportFileTSV, self).setUp()
        self.user = AuthUserFactory(fullname='Kenny Michel',
                                    username='Kenny@gmail.com')
        self.user2 = AuthUserFactory(fullname='alex queen')
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user2.affiliated_institutions.add(self.institution)
        self.user.save()
        self.user2.save()
        self.view = views.ExportFileTSV()

    def test_get(self):
        request = RequestFactory().get(
            'institutions:tsvexport',
            kwargs={'institution_id': self.institution.id})
        request.user = self.user
        view = setup_view(self.view, request,
                          institution_id=self.institution.id)
        res = view.get(request)

        result = res.content.decode('utf-8')

        nt.assert_equal(res.status_code, 200)
        nt.assert_equal(res['content-type'], 'text/tsv')
        nt.assert_in('kenny', result)
        nt.assert_in('alex queen', result)
        nt.assert_in('kenny@gmail.com', result)
