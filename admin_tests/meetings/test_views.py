from nose import tools as nt

from django.test import RequestFactory
from django.http import Http404
from modularodm import Q
from tests.base import AdminTestCase
from tests.factories import AuthUserFactory
from tests.test_conferences import ConferenceFactory
from website.conferences.model import Conference, DEFAULT_FIELD_NAMES

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


class TestMeetingFormView(AdminTestCase):
    def setUp(self):
        super(TestMeetingFormView, self).setUp()
        self.conf = ConferenceFactory()
        self.user = AuthUserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = MeetingFormView()
        mod_data = dict(data)
        mod_data.update({
            'edit': 'True',
            'endpoint': self.conf.endpoint,
            'admins': self.user.emails[0]
        })
        self.form = MeetingForm(data=mod_data)
        self.form.is_valid()

    def test_dispatch_raise_404(self):
        view = setup_form_view(self.view, self.request, self.form,
                               endpoint='meh')
        with nt.assert_raises(Http404):
            view.dispatch(self.request, endpoint='meh')

    def test_get_context(self):
        view = setup_form_view(self.view, self.request, self.form,
                               endpoint=self.conf.endpoint)
        view.conf = self.conf
        res = view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_in('endpoint', res)
        nt.assert_equal(res['endpoint'], self.conf.endpoint)

    def test_get_initial(self):
        view = setup_form_view(self.view, self.request, self.form,
                               endpoint=self.conf.endpoint)
        view.conf = self.conf
        res = view.get_initial()
        nt.assert_is_instance(res, dict)
        nt.assert_in('endpoint', res)
        nt.assert_in('field_submission2_plural', res)

    def test_form_valid(self):
        view = setup_form_view(self.view, self.request, self.form,
                               endpoint=self.conf.endpoint)
        view.conf = self.conf
        view.form_valid(self.form)
        self.conf.reload()
        nt.assert_equal(self.conf.admins[0].emails[0], self.user.emails[0])


class TestMeetingCreateFormView(AdminTestCase):
    def setUp(self):
        super(TestMeetingCreateFormView, self).setUp()
        Conference.remove()
        self.user = AuthUserFactory()
        self.request = RequestFactory().post('/fake_path')
        self.view = MeetingCreateFormView()
        mod_data = dict(data)
        mod_data.update({'admins': self.user.emails[0]})
        self.form = MeetingForm(data=mod_data)
        self.form.is_valid()

    def test_get_initial(self):
        self.view.get_initial()
        nt.assert_equal(self.view.initial['edit'], False)
        nt.assert_equal(self.view.initial['field_submission1'],
                        DEFAULT_FIELD_NAMES['submission1'])

    def test_form_valid(self):
        view = setup_form_view(self.view, self.request, self.form)
        view.form_valid(self.form)
        nt.assert_equal(
            Conference.find(Q('endpoint', 'iexact', data['endpoint'])).count(),
            1
        )


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
        emails = [user_1.emails[0], user_2.emails[0], user_3.emails[0]]
        res = get_admin_users(emails)
        nt.assert_in(user_1, res)
        nt.assert_in(user_2, res)
        nt.assert_in(user_3, res)
