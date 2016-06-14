import mock
from nose import tools as nt
from django.test import RequestFactory
from django.db import transaction
from django.http import Http404

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
    @mock.patch('admin.pre_reg.views.DraftRegistration.get_metadata_files')
    def setUp(self, mock_files):
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
    @mock.patch('admin.pre_reg.views.DraftRegistration.get_metadata_files')
    def setUp(self, mock_files):
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
    @mock.patch('admin.pre_reg.views.DraftRegistration.get_metadata_files')
    def setUp(self, mock_files):
        super(TestDraftFormView, self).setUp()
        self.user = AuthUserFactory()
        self.dr1 = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=utils.draft_reg_util(),
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

    def test_dispatch_raise_404(self):
        view = setup_view(DraftFormView(), self.request, draft_pk='wrong')
        with nt.assert_raises(Http404):
            view.dispatch(self.request)

    def test_get_initial(self):
        self.view.draft = self.dr1
        self.view.get_initial()
        res = self.view.initial
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['notes'], self.dr1.notes)
        nt.assert_equal(res['assignee'], self.dr1.flags['assignee'])
        nt.assert_equal(res['payment_sent'], self.dr1.flags['payment_sent'])
        nt.assert_equal(res['proof_of_publication'],
                        self.dr1.flags['proof_of_publication'])

    def test_get_context_data(self):
        self.view.draft = self.dr1
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_in('draft', res)
        nt.assert_is_instance(res['draft'], dict)
        nt.assert_in('IMMEDIATE', res)

    def test_form_valid_notes(self):
        form = DraftRegistrationForm(data=self.form_data)
        nt.assert_true(form.is_valid())
        view = setup_form_view(self.post_view, self.post, form,
                               draft_pk=self.dr1._id)
        view.draft = self.dr1
        count = OSFLogEntry.objects.count()
        with transaction.atomic():
            view.form_valid(form)
        nt.assert_equal(count, OSFLogEntry.objects.count())
        self.dr1.reload()
        nt.assert_equal(self.dr1.notes, self.form_data['notes'])

    @mock.patch('admin.pre_reg.views.DraftRegistration.approve')
    def test_form_valid_approve(self, mock_approve):
        self.form_data.update(approve_reject='approve')
        form = DraftRegistrationForm(data=self.form_data)
        nt.assert_true(form.is_valid())
        view = setup_form_view(self.post_view, self.post, form,
                               draft_pk=self.dr1._id)
        view.draft = self.dr1
        count = OSFLogEntry.objects.count()
        with transaction.atomic():
            view.form_valid(form)
        nt.assert_true(mock_approve.called)
        nt.assert_equal(count + 1, OSFLogEntry.objects.count())

    @mock.patch('admin.pre_reg.views.DraftRegistration.reject')
    def test_form_valid_reject(self, mock_reject):
        self.form_data.update(approve_reject='reject')
        form = DraftRegistrationForm(data=self.form_data)
        nt.assert_true(form.is_valid())
        view = setup_form_view(self.post_view, self.post, form,
                               draft_pk=self.dr1._id)
        view.draft = self.dr1
        count = OSFLogEntry.objects.count()
        with transaction.atomic():
            view.form_valid(form)
        nt.assert_true(mock_reject.called)
        nt.assert_equal(count + 1, OSFLogEntry.objects.count())


class TestCommentUpdateView(AdminTestCase):
    @mock.patch('admin.pre_reg.views.DraftRegistration.get_metadata_files')
    def setUp(self, mock_files):
        super(TestCommentUpdateView, self).setUp()
        self.user = AuthUserFactory()
        self.dr1 = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=utils.draft_reg_util(),
            registration_metadata=utils.SCHEMA_DATA
        )
        self.dr1.submit_for_review(self.user, {}, save=True)
        self.request = RequestFactory().post('/fake_path', data={'blah': 'arg'})
        self.request.user = UserFactory()
        self.view = CommentUpdateView()
        self.view = setup_view(self.view, self.request, draft_pk=self.dr1._id)

    @mock.patch('admin.pre_reg.views.json.loads')
    @mock.patch('admin.pre_reg.views.DraftRegistration.update_metadata')
    def test_post_comments(self, mock_json, mock_meta):
        count = OSFLogEntry.objects.count()
        self.view.post(self.request)
        nt.assert_equal(OSFLogEntry.objects.count(), count + 1)
