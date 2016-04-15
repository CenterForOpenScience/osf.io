from nose import tools as nt
from django.test import RequestFactory
from django.db import transaction

from tests.base import AdminTestCase
from tests.factories import (
    DraftRegistrationFactory,
    AuthUserFactory,
    DraftRegistration,
)
from admin_tests.utilities import setup_view, setup_form_view
from admin_tests.factories import UserFactory
from admin_tests.pre_reg import utils

from admin.pre_reg.views import (
    DraftListView,
    DraftDetailView,
    DraftFormView,
    CommentUpdateView,
)
from admin.pre_reg.forms import DraftRegistrationForm
from admin.common_auth.logs import OSFLogEntry


class TestDraftListView(AdminTestCase):
    def setUp(self):
        super(TestDraftListView, self).setUp()
        self.user = AuthUserFactory()
        schema = utils.draft_reg_util()
        self.dr1 = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=schema,
            registration_metadata=utils.SCHEMA_DATA
        )
        self.dr1.submit_for_review(self.user, {}, save=True)
        self.dr2 = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=schema,
            registration_metadata=utils.SCHEMA_DATA
        )
        self.dr2.submit_for_review(self.user, {}, save=True)
        self.request = RequestFactory().get('/fake_path')
        self.view = DraftListView()
        self.view = setup_view(self.view, self.request)

    def test_get_queryset(self):
        res = list(self.view.get_queryset())
        nt.assert_equal(len(res), 2)
        nt.assert_is_instance(res[0], DraftRegistration)

    def test_get_context_data(self):
        self.view.object_list = self.view.get_queryset()
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_is_instance(res['drafts'], list)
        nt.assert_equal(len(res['drafts']), 2)


class TestDraftDetailView(AdminTestCase):
    def setUp(self):
        super(TestDraftDetailView, self).setUp()
        self.user = AuthUserFactory()
        schema = utils.draft_reg_util()
        self.dr1 = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=schema,
            registration_metadata=utils.SCHEMA_DATA
        )
        self.dr1.submit_for_review(self.user, {}, save=True)
        self.request = RequestFactory().get('/fake_path')
        self.view = DraftDetailView()
        self.view = setup_view(self.view, self.request, draft_pk=self.dr1._id)

    def test_get_object(self):
        res = self.view.get_object()
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['pk'], self.dr1._id)


class TestDraftFormView(AdminTestCase):
    def setUp(self):
        super(TestDraftFormView, self).setUp()
        self.user = AuthUserFactory()
        schema = utils.draft_reg_util()
        self.dr1 = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=schema,
            registration_metadata=utils.SCHEMA_DATA
        )
        self.dr1.submit_for_review(self.user, {}, save=True)
        self.dr1.flags  # sets flags if there aren't any yet.
        self.request = RequestFactory().get('/fake_path')
        self.view = DraftFormView()
        self.view = setup_view(self.view, self.request, draft_pk=self.dr1._id)

        self.post = RequestFactory().post('/fake_path')
        self.post.user = UserFactory()
        self.post_view = DraftFormView()
        self.form_data = {
            'notes': 'Far between',
            'proof_of_publication': 'approved',
        }

    def test_get_initial(self):
        self.view.get_initial()
        res = self.view.initial
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['notes'], self.dr1.notes)
        nt.assert_equal(res['assignee'], self.dr1.flags['assignee'])
        nt.assert_equal(res['payment_sent'], self.dr1.flags['payment_sent'])
        nt.assert_equal(res['proof_of_publication'],
                        self.dr1.flags['proof_of_publication'])

    def test_get_context_data(self):
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_in('draft', res)
        nt.assert_is_instance(res['draft'], dict)
        nt.assert_in('IMMEDIATE', res)

    def test_form_valid_notes_and_stuff(self):
        form = DraftRegistrationForm(data=self.form_data)
        nt.assert_true(form.is_valid())
        view = setup_form_view(self.post_view, self.post, form,
                               draft_pk=self.dr1._id)
        count = OSFLogEntry.objects.count()
        with transaction.atomic():
            view.form_valid(form)
        nt.assert_equal(count, OSFLogEntry.objects.count())
        self.dr1.reload()
        nt.assert_equal(self.dr1.notes, self.form_data['notes'])


# class TestPreReg(AdminTestCase):
#     def setUp(self):
#         super(TestPreReg, self).setUp()
#         self.request = RequestFactory().post('/nothing', data={'bleh': 'arg'})
#         self.request.user = UserFactory
#
#     @mock.patch('admin.pre_reg.views.DraftRegistration.approve')
#     @mock.patch('admin.pre_reg.views.csrf_exempt')
#     @mock.patch('admin.pre_reg.views.get_draft_or_error')
#     def test_add_log_approve(self, mock_1, mock_2, mock_3):
#         count = OSFLogEntry.objects.count()
#         approve_draft(self.request, 1)
#         nt.assert_equal(OSFLogEntry.objects.count(), count + 1)
#
#     @mock.patch('admin.pre_reg.views.DraftRegistration.approve')
#     @mock.patch('admin.pre_reg.views.csrf_exempt')
#     @mock.patch('admin.pre_reg.views.get_draft_or_error')
#     def test_add_log_reject(self, mock_1, mock_2, mock_3):
#         count = OSFLogEntry.objects.count()
#         reject_draft(self.request, 1)
#         nt.assert_equal(OSFLogEntry.objects.count(), count + 1)
