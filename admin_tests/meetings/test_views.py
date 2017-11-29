from nose import tools as nt

from django.test import RequestFactory
from django.http import Http404
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied

from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory
from tests.test_conferences import ConferenceFactory
from osf.models.conference import Conference, DEFAULT_FIELD_NAMES

from admin_tests.utilities import setup_form_view
from admin_tests.meetings.test_forms import data
from admin.meetings.views import (
    MeetingListView,
    MeetingCreateFormView,
    MeetingFormView,
    get_custom_fields,
    get_admin_users,
)
from admin.meetings.forms import MeetingForm


class TestMeetingListView(AdminTestCase):
    def setUp(self):
        super(TestMeetingListView, self).setUp()
        Conference.remove()
        ConferenceFactory()
        ConferenceFactory()
        ConferenceFactory()

    def test_get_queryset(self):
        view = MeetingListView()
        nt.assert_equal(len(view.get_queryset()), 3)

    def test_no_user_permissions_raises_error(self):
        user = AuthUserFactory()
        request = RequestFactory().get(reverse('meetings:list'))
        request.user = user

        with nt.assert_raises(PermissionDenied):
            MeetingListView.as_view()(request)

    def test_correct_view_permissions(self):
        user = AuthUserFactory()

        view_permission = Permission.objects.get(codename='view_conference')
        user.user_permissions.add(view_permission)
        user.save()

        request = RequestFactory().get(reverse('meetings:list'))
        request.user = user

        response = MeetingListView.as_view()(request)
        nt.assert_equal(response.status_code, 200)


class TestMeetingFormView(AdminTestCase):
    def setUp(self):
        super(TestMeetingFormView, self).setUp()
        self.conf = ConferenceFactory()
        self.user = AuthUserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = MeetingFormView
        mod_data = dict(data)
        mod_data.update({
            'edit': 'True',
            'endpoint': self.conf.endpoint,
            'admins': self.user.emails.first().address,
            'location': 'Timbuktu, Mali',
            'start date': 'Dec 11 2014',
            'end_date': 'Jan 12 2013'
        })
        self.form = MeetingForm(data=mod_data)
        self.form.is_valid()

        self.url = reverse('meetings:detail', kwargs={'endpoint': self.conf.endpoint})

    def test_dispatch_raise_404(self):
        view = setup_form_view(self.view(), self.request, self.form,
                               endpoint='meh')
        with nt.assert_raises(Http404):
            view.dispatch(self.request, endpoint='meh')

    def test_get_context(self):
        view = setup_form_view(self.view(), self.request, self.form,
                               endpoint=self.conf.endpoint)
        view.conf = self.conf
        res = view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_in('endpoint', res)
        nt.assert_equal(res['endpoint'], self.conf.endpoint)

    def test_get_initial(self):
        view = setup_form_view(self.view(), self.request, self.form,
                               endpoint=self.conf.endpoint)
        view.conf = self.conf
        res = view.get_initial()
        nt.assert_is_instance(res, dict)
        nt.assert_in('endpoint', res)
        nt.assert_in('submission2_plural', res)

    def test_form_valid(self):
        view = setup_form_view(self.view(), self.request, self.form,
                               endpoint=self.conf.endpoint)
        view.conf = self.conf
        view.form_valid(self.form)
        self.conf.reload()
        nt.assert_equal(self.conf.admins.all()[0].emails.first().address, self.user.emails.first().address)
        nt.assert_equal(self.conf.location, self.form.cleaned_data['location'])
        nt.assert_equal(self.conf.start_date, self.form.cleaned_data['start_date'])

    def test_no_user_permissions_raises_error(self):
        request = RequestFactory().get(self.url)
        request.user = self.user

        with nt.assert_raises(PermissionDenied):
            self.view.as_view()(request, endpoint=self.conf.endpoint)

    def test_correct_view_permissions(self):

        view_permission = Permission.objects.get(codename='change_conference')
        self.user.user_permissions.add(view_permission)
        self.user.save()

        request = RequestFactory().get(self.url)
        request.user = self.user

        response = self.view.as_view()(request, endpoint=self.conf.endpoint)
        nt.assert_equal(response.status_code, 200)


class TestMeetingCreateFormView(AdminTestCase):
    def setUp(self):
        super(TestMeetingCreateFormView, self).setUp()
        Conference.remove()
        self.user = AuthUserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = MeetingCreateFormView
        mod_data = dict(data)
        mod_data.update({'admins': self.user.emails.first().address})
        self.form = MeetingForm(data=mod_data)
        self.form.is_valid()

        self.url = reverse('meetings:create')

    def test_get_initial(self):
        self.view().get_initial()
        nt.assert_equal(self.view().initial['edit'], False)
        nt.assert_equal(self.view.initial['submission1'],
                        DEFAULT_FIELD_NAMES['submission1'])

    def test_form_valid(self):
        view = setup_form_view(self.view(), self.request, self.form)
        view.form_valid(self.form)
        nt.assert_equal(Conference.objects.filter(endpoint=data['endpoint']).count(), 1)

    def test_no_user_permissions_raises_error(self):
        request = RequestFactory().get(self.url)
        request.user = self.user

        with nt.assert_raises(PermissionDenied):
            self.view.as_view()(request)

    def test_correct_view_permissions(self):
        change_permission = Permission.objects.get(codename='view_conference')
        view_permission = Permission.objects.get(codename='change_conference')
        self.user.user_permissions.add(view_permission)
        self.user.user_permissions.add(change_permission)
        self.user.save()

        request = RequestFactory().get(self.url)
        request.user = self.user

        response = self.view.as_view()(request)
        nt.assert_equal(response.status_code, 200)


class TestMeetingMisc(AdminTestCase):
    def test_get_custom_fields(self):
        res1, res2 = get_custom_fields(data)
        nt.assert_is_instance(res1, dict)
        nt.assert_is_instance(res2, dict)
        for key in res1.keys():
            nt.assert_not_in('field', key)

    def test_get_admin_users(self):
        user_1 = AuthUserFactory()
        user_2 = AuthUserFactory()
        user_3 = AuthUserFactory()
        emails = [user_1.emails.first().address, user_2.emails.first().address, user_3.emails.first().address]
        res = get_admin_users(emails)
        nt.assert_in(user_1, res)
        nt.assert_in(user_2, res)
        nt.assert_in(user_3, res)
