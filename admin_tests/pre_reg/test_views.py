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
    ProjectFactory,
)
from website.files.models import OsfStorageFileNode
from website.project.model import ensure_schemas
from website.prereg.utils import get_prereg_schema

from admin_tests.utilities import setup_view, setup_form_view, setup_user_view
from admin_tests.factories import UserFactory
from admin_tests.pre_reg import utils

from admin.pre_reg.views import (
    DraftListView,
    DraftDetailView,
    DraftFormView,
    CommentUpdateView,
    get_metadata_files,
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

    @mock.patch('admin.pre_reg.views.DraftDetailView.checkout_files')
    def test_get_object(self, mock_files):
        res = self.view.get_object()
        nt.assert_is_instance(res, dict)
        nt.assert_equal(res['pk'], self.dr1._id)


class TestDraftFormView(AdminTestCase):
    def setUp(self):
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

    @mock.patch('admin.pre_reg.views.DraftFormView.checkin_files')
    @mock.patch('admin.pre_reg.views.DraftRegistration.approve')
    def test_form_valid_approve(self, mock_approve, mock_files):
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

    @mock.patch('admin.pre_reg.views.DraftFormView.checkin_files')
    @mock.patch('admin.pre_reg.views.DraftRegistration.reject')
    def test_form_valid_reject(self, mock_reject, mock_files):
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
    def setUp(self):
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


class TestPreregFiles(AdminTestCase):
    def setUp(self):
        super(TestPreregFiles, self).setUp()
        self.prereg_user = AuthUserFactory()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)

        ensure_schemas()
        prereg_schema = get_prereg_schema()
        self.d_of_qs = {
            'q7': OsfStorageFileNode(node=self.node, name='7'),
            'q11': OsfStorageFileNode(node=self.node, name='11'),
            'q16': OsfStorageFileNode(node=self.node, name='16'),
            'q12': OsfStorageFileNode(node=self.node, name='12'),
            'q13': OsfStorageFileNode(node=self.node, name='13'),
            'q19': OsfStorageFileNode(node=self.node, name='19'),
            'q26': OsfStorageFileNode(node=self.node, name='26')
        }
        data = {}
        for q, f in self.d_of_qs.iteritems():
            f.get_guid(create=True)
            f.save()
            data[q] = {
                'value': {
                    'uploader': {
                        'extra': [
                            {
                                'data': {
                                    'provider': 'osfstorage',
                                    'path': f.path,
                                    'fileId': f._id
                                }
                            }
                        ]
                    }
                }
            }
        self.draft = DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=prereg_schema,
            registration_metadata=data
        )
        self.prereg_user.save()
        self.admin_user = UserFactory(osf_id=self.prereg_user.pk)

    def test_checkout_files(self):
        self.draft.submit_for_review(self.user, {}, save=True)
        request = RequestFactory().get('/fake_path')
        view = DraftDetailView()
        view = setup_user_view(view, request, self.admin_user,
                               draft_pk=self.draft._id)
        view.checkout_files(self.draft)
        for q, f in self.d_of_qs.iteritems():
            nt.assert_equal(self.prereg_user, f.checkout)

    def test_checkin_files(self):
        self.draft.submit_for_review(self.user, {}, save=True)
        request = RequestFactory().get('/fake_path')
        view = DraftDetailView()
        view = setup_user_view(view, request, self.admin_user,
                               draft_pk=self.draft._id)
        view.checkout_files(self.draft)
        view2 = DraftFormView()
        view2 = setup_view(view2, request, draft_pk=self.draft._id)
        view2.checkin_files(self.draft)
        for q, f in self.d_of_qs.iteritems():
            nt.assert_equal(None, f.checkout)

    def test_get_meta_data_files(self):
        for item in get_metadata_files(self.draft):
            nt.assert_is_instance(item, OsfStorageFileNode)
