from datetime import datetime
import mock
import pytest
from django.contrib.sessions.middleware import SessionMiddleware

from admin.user_emails import views
from admin.user_emails.forms import UserEmailsSearchForm
from admin_tests.utilities import setup_view, setup_form_view
from django.contrib.auth.models import Permission
from django.test import RequestFactory
from django.urls import reverse
from framework.exceptions import HTTPError
from nose import tools as nt
from osf.models.user import OSFUser, Email
from osf_tests.factories import (
    UserFactory,
    AuthUserFactory, InstitutionFactory
)
from tests.base import AdminTestCase

pytestmark = pytest.mark.django_db


class TestUserEmailsFormView(AdminTestCase):

    def setUp(self):
        self.user_1 = AuthUserFactory(fullname='Broken Matt Hardy')
        self.user_2 = AuthUserFactory(fullname='Jeff Hardy')
        self.user_3 = AuthUserFactory(fullname='Reby Sky')
        self.user_4 = AuthUserFactory(fullname='King Maxel Hardy')

        self.user_2_alternate_email = 'brothernero@delapidatedboat.com'
        self.user_2.emails.create(address=self.user_2_alternate_email)
        self.user_2.save()
        self.view_permission = views.UserEmailsFormView
        self.request = RequestFactory().get('/fake_path')
        self.view = views.UserEmailsFormView()

        self.view = setup_form_view(self.view,
                                    self.request, form=UserEmailsSearchForm())

    def test_form_valid_search_user_by_guid(self):
        form_data = {
            'guid': self.user_1.guids.first()._id
        }
        form = UserEmailsSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(
            self.view.success_url,
            '/user-emails/search/guid/{}/'.format(
                self.user_1.guids.first()._id
            )
        )

    def test_form_valid_search_user_by_name(self):
        form_data = {
            'name': 'Hardy'
        }
        form = UserEmailsSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(
            self.view.success_url,
            '/user-emails/search/name/Hardy/'
        )

    def test_form_valid_search_user_by_name_with_punctuation(self):
        form_data = {
            'name': 'Dr. Sportello-Fay, PI @, #, $, %, ^, &, *, (, ), ~'
        }
        form = UserEmailsSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        _url = '/user-emails/search/name/Dr.%20Sportello-Fay,' \
               '%20PI%20@,%20%23,%20$,%20%25,%20%5E,%20&,%20*,%20(,%20),%20~/'
        nt.assert_equal(self.view.success_url, _url)

    def test_form_valid_search_user_by_username(self):
        form_data = {
            'email': self.user_1.username
        }
        form = UserEmailsSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(
            self.view.success_url,
            '/user-emails/search/guid/{}/'.format(
                self.user_1.guids.first()._id
            )
        )

    @mock.patch('admin.user_emails.views.UserEmailsFormView.is_admin')
    def test_form_valid_is_admin(self, mock_is_admin):
        mock_is_admin.return_value = True

        request = RequestFactory().get('/fake_path')
        user_1 = AuthUserFactory(fullname='Broken Matt Hardy')

        form_data = {
            'email': user_1.username
        }
        institution = InstitutionFactory()
        user_1.affiliated_institutions.add(institution)

        request.user = user_1
        view = views.UserEmailsFormView()

        view = setup_form_view(view, request, form=UserEmailsSearchForm())

        form = UserEmailsSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = view.form_valid(form)

        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(
            view.success_url,
            '/user-emails/search/guid/{}/'.format(user_1.guids.first()._id)
        )

    def test_form_valid_search_user_by_alternate_email(self):
        form_data = {
            'email': self.user_2_alternate_email
        }
        form = UserEmailsSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(
            self.view.success_url,
            '/user-emails/search/guid/{}/'.format(
                self.user_2.guids.first()._id
            )
        )

    def test_form_valid_search_user_list_case_insensitive(self):
        view = views.UserEmailsSearchList()
        view = setup_view(view, self.request)
        view.kwargs = {'name': 'hardy'}

        results = view.get_queryset()

        nt.assert_equal(len(results), 3)
        for user in results:
            nt.assert_in('Hardy', user.fullname)

    def test_form_valid_search_user_by_email_not_found(self):
        form_data = {
            'email': 'abcd@gmail.com'
        }
        form = UserEmailsSearchForm(data=form_data)
        nt.assert_true(form.is_valid())
        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 404)

    @mock.patch('admin.user_emails.views.OSFUser.objects')
    def test_form_valid_with_multiple_OSFUser_returned(self, mockOSFUser):
        name = 'test'
        email = 'test@mail.com'
        data = {'name': name, 'email': email}

        mockOSFUser.filter.return_value.filter.return_value.\
            distinct.return_value.get.\
            side_effect = OSFUser.MultipleObjectsReturned

        form = UserEmailsSearchForm(data=data)
        nt.assert_true(form.is_valid())

        response = self.view.form_valid(form)
        nt.assert_equal(response.status_code, 404)

    def test_TestUserEmailsFormView_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        change_permission = Permission.objects.get(codename='view_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().get(reverse('user-emails:search'))
        request.user = user

        response = self.view_permission.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)

    def test_init_method(self):
        view = views.UserEmailsFormView()
        self.assertEqual(view.redirect_url, '/user-emails/')


class TestUserEmailSearchList(AdminTestCase):

    def setUp(self):
        self.user_1 = AuthUserFactory(fullname='Broken Matt Hardy')
        self.user_2 = AuthUserFactory(fullname='Jeff Hardy')
        self.user_3 = AuthUserFactory(fullname='Reby Sky')
        self.user_4 = AuthUserFactory(fullname='King Maxel Hardy')

        self.user_2_alternate_email = 'brothernero@delapidatedboat.com'
        self.user_2.emails.create(address=self.user_2_alternate_email)
        self.user_2.save()
        self.view_permission = views.UserEmailsSearchList
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user_1

    def test_get_queryset_method(self):
        view = views.UserEmailsSearchList()
        view = setup_view(view, self.request)
        view.kwargs = {'name': 'Hardy'}

        results = view.get_queryset()

        nt.assert_equal(len(results), 3)
        for user in results:
            nt.assert_in('Hardy', user.fullname)

    def test_get_queryset_method_not_keyword(self):
        view = views.UserEmailsSearchList()
        view = setup_view(view, self.request)
        view.kwargs = {'name': ''}

        with nt.assert_raises(HTTPError) as exc_info:
            view.get_queryset()

        nt.assert_equal(exc_info.exception.code, 400)

    @mock.patch('admin.user_emails.views.UserEmailsSearchList.is_admin')
    def test_get_queryset_method_is_admin(self, mock_is_admin):
        mock_is_admin.return_value = True
        institution = InstitutionFactory()
        self.user_1.affiliated_institutions.add(institution)
        view = views.UserEmailsSearchList()

        view = setup_view(view, self.request)
        view.kwargs = {'name': 'Hardy'}

        results = view.get_queryset()
        for user in results:
            nt.assert_in(self.user_1.fullname, user.fullname)

    def test_get_context_data_method(self):
        view = views.UserEmailsSearchList()
        view = setup_view(view, self.request)
        data = {'name': 'Broken Matt Hardy', 'is_disabled': False}
        view.kwargs = data
        view.object_list = [{'name': 'Broken Matt Hardy'}]
        result = view.get_context_data()

        nt.assert_is_instance(result, dict)
        nt.assert_equal(result['users'][0]['name'], data['name'])
        nt.assert_equal(result['object_list'][0]['name'], data['name'])

    @pytest.mark.skip
    def test_get_context_data_method_with_user_is_disabled_equal_True(self):
        view = views.UserEmailsSearchList()
        view = setup_view(view, self.request)
        data = {'name': 'Broken Matt Hardy', 'is_disabled': True,
                'date_disabled': datetime(2022, 2, 14)}
        view.kwargs = data
        view.object_list = [{'name': 'Broken Matt Hardy'}]
        result = view.get_context_data()

        nt.assert_equal(result['users'][0]['name'], data['name'])
        nt.assert_equal(result['object_list'][0]['name'], data['name'])
        nt.assert_equal(result['users'][0]['disabled'], data['date_disabled'])

    def test_UserEmailsSearchList_with_correct_view_permissions(self):
        user = UserFactory()

        change_permission = Permission.objects.get(codename='view_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().get(reverse('user-emails:search_list',
                                               kwargs={'name': 'Hardy'}))
        request.user = user
        self.view_permission.kwargs = {'name': 'Hardy'}

        response = self.view_permission.as_view()(request, name='Hardy')
        self.assertEqual(response.status_code, 200)


def add_session_to_request(request):
    """Annotate a request object with a session"""
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()


class TestUserEmailsView(AdminTestCase):
    def setUp(self):
        super(TestUserEmailsView, self).setUp()
        self.user = UserFactory()
        self.user.save()
        self.request = RequestFactory().get('/fake_path')
        add_session_to_request(self.request)
        self.request.user = self.user
        self.plain_view = views.UserEmailsView
        self.view = views.UserEmailsView()

    def test_UserEmailsView_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        view_permission = Permission.objects.get(codename='view_osfuser')
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().get(reverse('user-emails:user',
                                               kwargs={'guid': guid}))
        add_session_to_request(request)
        request.user = user

        response = views.UserEmailsView.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 200)

    def test_get_object(self):
        self.view.kwargs = {'guid': self.user._id}
        self.request.user = self.user
        self.view.request = self.request
        result = self.view.get_object()

        nt.assert_is_instance(result, dict)
        nt.assert_equal(result['username'], self.user.username)
        nt.assert_equal(result['name'], self.user.fullname)
        nt.assert_equal(result['id'], self.user._id)
        nt.assert_equal(list(result['emails']), list(
            self.user.emails.values_list('address', flat=True)))

    def test_get_object_is_admin(self):
        self.view.kwargs = {'guid': self.user._id}
        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        self.request.user = self.user
        self.view.request = self.request
        result = self.view.get_object()
        view = views.UserEmailsView
        view.is_admin = True

        response = view.as_view()(
            self.request,
            guid=self.user._id
        )

        nt.assert_equal(response.status_code, 200)
        nt.assert_is_instance(result, dict)
        nt.assert_equal(result['username'], self.user.username)
        nt.assert_equal(result['name'], self.user.fullname)
        nt.assert_equal(result['id'], self.user._id)
        nt.assert_equal(list(result['emails']), list(
            self.user.emails.values_list('address', flat=True)))

    def test_get_object_pk_not_in_all_institution_users_id(self):
        self.view.kwargs = {'guid': self.user._id}
        self.request.user = self.user
        self.view.request = self.request
        view = views.UserEmailsView
        view.is_admin = True

        with nt.assert_raises(HTTPError) as exc_info:
            self.view.get_object()
        nt.assert_equal(exc_info.exception.code, 403)

    def test_get_context_data(self):
        self.view.request = self.request
        self.view.object = self.user
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)


class TestUserPrimaryEmail(AdminTestCase):
    def setUp(self):
        super(TestUserPrimaryEmail, self).setUp()

        self.user = UserFactory()
        self.user.username = 'email@gmail.com'
        self.user.emails.create(address='alternate1@gmail.com')
        self.user.emails.create(address='alternate2@gmail.com')
        self.user.emails.create(address='Email@gmail.com')
        change_permission = Permission.objects.get(codename='view_osfuser')
        self.user.user_permissions.add(change_permission)
        self.user.save()
        self.view = views.UserPrimaryEmail.as_view()
        self.view_permission = views.UserPrimaryEmail

    def test_post_missing_parameter(self):
        request = RequestFactory().post(reverse(
            'user-emails:primary', kwargs={'guid': self.user._id}))
        request.user = self.user

        response = self.view(
            request,
            guid=self.user._id
        )
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, '/user-emails/{}/'.format(self.user._id))

    def test_post_primary_email_not_in_email_list(self):
        primary_email = 'test@gmail.com'
        request = RequestFactory().post(
            reverse('user-emails:primary', kwargs={'guid': self.user._id}),
            {'primary_email': primary_email})
        request.user = self.user

        response = self.view(
            request,
            guid=self.user._id
        )
        is_exist = Email.objects.filter(address=primary_email).exists()
        assert is_exist is True
        nt.assert_equal(response.url, '/user-emails/{}/'.format(self.user._id))

    def test_post_alternate_email_equal_primary_email(self):
        request = RequestFactory().post(
            reverse('user-emails:primary', kwargs={'guid': self.user._id}),
            {'primary_email': 'email@gmail.com'})
        request.user = self.user

        response = self.view(
            request,
            guid=self.user._id
        )
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, '/user-emails/{}/'.format(self.user._id))

    @mock.patch('admin.user_emails.views.mailchimp_utils.'
                'unsubscribe_mailchimp_async')
    def test_post_find_subscription(self, mockApi):
        request = RequestFactory().post(
            reverse('user-emails:primary', kwargs={'guid': self.user._id}),
            {'primary_email': 'alternate1@gmail.com'})
        self.user.mailchimp_mailing_lists = {'list_name': 'Value1',
                                             'subscription': 'value2'}
        self.user.save()
        request.user = self.user
        mockApi.return_value = 'Call it'

        self.view(request, guid=self.user._id)

        mockApi.assert_called()

    @mock.patch('admin.user_emails.views.mailchimp_utils.'
                'unsubscribe_mailchimp_async')
    def test_post_not_found_subscription(self, mockApi):
        request = RequestFactory().post(
            reverse('user-emails:primary', kwargs={'guid': self.user._id}),
            {'primary_email': 'alternate1@gmail.com'})
        self.user.mailchimp_mailing_lists = {}
        self.user.save()
        request.user = self.user
        mockApi.return_value = 'Call it'

        self.view(request, guid=self.user._id)

        mockApi.assert_not_called()

    def test_UserPrimaryEmail_correct_view_permissions(self):
        user = UserFactory()
        guid = user._id

        change_permission = Permission.objects.get(codename='view_osfuser')
        user.user_permissions.add(change_permission)
        user.save()

        request = RequestFactory().post(reverse('user-emails:primary',
                                                kwargs={'guid': guid}))
        request.user = user

        response = self.view_permission.as_view()(request, guid=guid)
        self.assertEqual(response.status_code, 302)

    @mock.patch('admin.user_emails.views.UserPrimaryEmail.is_admin')
    def test_post_is_admin(self, mock_is_admin):
        mock_is_admin.return_value = True
        user = UserFactory()
        request = RequestFactory().post(reverse('user-emails:primary',
                                                kwargs={'guid': user._id}))
        institution = InstitutionFactory()
        user.affiliated_institutions.add(institution)
        request.user = user

        # view = views.UserPrimaryEmail
        # view.is_admin = True

        response = self.view(
            request,
            guid=user._id
        )
        nt.assert_equal(response.status_code, 302)
        nt.assert_equal(response.url, '/user-emails/{}/'.format(user._id))

    @mock.patch('admin.user_emails.views.UserPrimaryEmail.is_admin')
    def test_post_permission_denied(self, mock_is_admin):
        mock_is_admin.return_value = True
        request = RequestFactory().post(reverse(
            'user-emails:primary', kwargs={'guid': self.user._id}))
        request.user = self.user

        response = self.view(
            request,
            guid=self.user._id
        )
        nt.assert_equal(response.status_code, 403)
