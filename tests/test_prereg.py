from nose.tools import *  # noqa

from modularodm import Q

from website.prereg import prereg_landing_page as landing_page
from website.prereg.utils import drafts_for_user
from website.project.model import ensure_schemas, MetaSchema

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
                'campaign_long': 'Prereg Challenge',
                'campaign_short': 'prereg',
            }
        )

    def test_has_project(self):
        factories.ProjectFactory(creator=self.user)

        assert_equal(
            landing_page(user=self.user),
            {
                'has_projects': True,
                'has_draft_registrations': False,
                'campaign_long': 'Prereg Challenge',
                'campaign_short': 'prereg',
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
                'campaign_long': 'Prereg Challenge',
                'campaign_short': 'prereg',
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
        drafts = drafts_for_user(self.user, 'prereg')
        for d in drafts:
            assert_in(d._id, (d2._id, d3._id))
            assert_not_equal(d._id, d1._id)
