from nose.tools import *  # noqa
import mock

from modularodm import Q

from website.prereg import prereg_landing_page as landing_page, drafts_for_user
from website.project.model import ensure_schemas, MetaSchema
from website import settings
from website.files.models.osfstorage import OsfStorageFileNode
from website.prereg.utils import get_prereg_schema
from framework.auth.core import Auth

from tests.base import OsfTestCase
from tests import factories


class PreregLandingPageTestCase(OsfTestCase):
    def setUp(self):
        super(PreregLandingPageTestCase, self).setUp()
        ensure_schemas()
        self.user = factories.UserFactory()

    def test_no_projects(self):
        assert_equal(
            landing_page(user=self.user),
            {
                'has_projects': False,
                'has_draft_registrations': False,
            }
        )

    def test_has_project(self):
        factories.ProjectFactory(creator=self.user)

        assert_equal(
            landing_page(user=self.user),
            {
                'has_projects': True,
                'has_draft_registrations': False,
            }
        )

    def test_has_project_and_draft_registration(self):
        prereg_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge')
        )
        factories.DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=prereg_schema
        )

        assert_equal(
            landing_page(user=self.user),
            {
                'has_projects': True,
                'has_draft_registrations': True,
            }
        )

    def test_drafts_for_user_omits_registered(self):
        prereg_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )

        d1 = factories.DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=prereg_schema
        )
        d2 = factories.DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=prereg_schema
        )
        d3 = factories.DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=prereg_schema
        )
        d1.registered_node = factories.ProjectFactory()
        d1.save()
        drafts = drafts_for_user(self.user)
        for d in drafts:
            assert_in(d._id, (d2._id, d3._id))
            assert_not_equal(d._id, d1._id)


class TestPreregFiles(OsfTestCase):
    def setUp(self):
        super(TestPreregFiles, self).setUp()
        self.prereg_user = factories.AuthUserFactory()
        self.user = factories.AuthUserFactory()
        self.node = factories.ProjectFactory(creator=self.user)

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
            f.save()
            data[q] = {
                'value': {
                    'uploader': {
                        'extra': [{
                            'data': {
                                'provider': 'osfstorage',
                                'path': f.path
                            }
                        }]
                        }
                    }
                }
        self.draft = factories.DraftRegistrationFactory(
            initiator=self.user,
            registration_schema=prereg_schema,
            registration_metadata=data
        )
        settings.PREREG_FILE_CHECKOUT_USER = self.prereg_user.pk
        self.prereg_user.system_tags.append(settings.PREREG_ADMIN_TAG)
        self.prereg_user.save()

    def test_checkout_files(self):
        self.draft.checkout_files(save=True)
        for q, f in self.d_of_qs.iteritems():
            assert_equal(self.prereg_user, f.checkout)

    def test_checkin_files(self):
        self.draft.checkout_files(save=True)
        self.draft.checkin_files(save=True)
        for q, f in self.d_of_qs.iteritems():
            assert_equal(None, f.checkout)

    def test_submit_for_review_checkout(self):
        self.draft.submit_for_review(self.user, None, save=True)
        for q, f in self.d_of_qs.iteritems():
            assert_equal(self.prereg_user, f.checkout)

    @mock.patch('website.project.model.DraftRegistrationApproval.approve')
    def test_approve_checkin(self, mock_approve):
        self.draft.submit_for_review(self.user, None, save=True)
        self.draft.approve(self.prereg_user)
        for q, f in self.d_of_qs.iteritems():
            assert_equal(None, f.checkout)

    def test_reject_checkin(self):
        self.draft.submit_for_review(self.user, None, save=True)
        self.draft.reject(self.prereg_user)
        for q, f in self.d_of_qs.iteritems():
            assert_equal(None, f.checkout)

    @mock.patch('website.project.model.Node.register_node')
    def test_register_checkin(self, mock_register_node):
        self.draft.submit_for_review(self.user, None, save=True)
        self.draft.register(Auth(self.user))
        for q, f in self.d_of_qs.iteritems():
            assert_equal(None, f.checkout)
