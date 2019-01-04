from nose.tools import *  # noqa: F403

from waffle.testutils import override_switch

from osf.models import RegistrationSchema
from osf.features import OSF_PREREGISTRATION
from website.prereg import prereg_landing_page as landing_page
from website.prereg.utils import get_prereg_schema
from website.registries.utils import drafts_for_user

from tests.base import OsfTestCase
from osf_tests import factories


class TestPreregLandingPage(OsfTestCase):
    def setUp(self):
        super(TestPreregLandingPage, self).setUp()
        self.user = factories.UserFactory()

    def test_not_logged_in(self):
        assert_equal(
            landing_page(),
            {
                'has_projects': False,
                'has_draft_registrations': False,
                'campaign_long': 'Prereg Challenge',
                'campaign_short': 'prereg_challenge',
                'is_logged_in': False,
            }
        )

        with override_switch(name=OSF_PREREGISTRATION, active=True):
            assert_equal(
                landing_page(),
                {
                    'has_projects': False,
                    'has_draft_registrations': False,
                    'campaign_long': 'OSF Preregistration',
                    'campaign_short': 'prereg',
                    'is_logged_in': False,
                }
            )

    def test_no_projects(self):
        assert_equal(
            landing_page(user=self.user),
            {
                'has_projects': False,
                'has_draft_registrations': False,
                'campaign_long': 'Prereg Challenge',
                'campaign_short': 'prereg_challenge',
                'is_logged_in': True,
            }
        )

        with override_switch(name=OSF_PREREGISTRATION, active=True):
            assert_equal(
                landing_page(user=self.user),
                {
                    'has_projects': False,
                    'has_draft_registrations': False,
                    'campaign_long': 'OSF Preregistration',
                    'campaign_short': 'prereg',
                    'is_logged_in': True,
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
                'campaign_short': 'prereg_challenge',
                'is_logged_in': True,
            }
        )

        with override_switch(name=OSF_PREREGISTRATION, active=True):
            assert_equal(
                landing_page(user=self.user),
                {
                    'has_projects': True,
                    'has_draft_registrations': False,
                    'campaign_long': 'OSF Preregistration',
                    'campaign_short': 'prereg',
                    'is_logged_in': True,
                }
            )

    def test_has_project_and_draft_registration(self):
        prereg_schema = RegistrationSchema.objects.get(name='Prereg Challenge')
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
                'campaign_short': 'prereg_challenge',
                'is_logged_in': True,
            }
        )

        with override_switch(name=OSF_PREREGISTRATION, active=True):
            prereg_schema = RegistrationSchema.objects.get(name='OSF Preregistration')
            factories.DraftRegistrationFactory(
                initiator=self.user,
                registration_schema=prereg_schema
            )
            assert_equal(
                landing_page(user=self.user),
                {
                    'has_projects': True,
                    'has_draft_registrations': True,
                    'campaign_long': 'OSF Preregistration',
                    'campaign_short': 'prereg',
                    'is_logged_in': True,
                }
            )

    def test_drafts_for_user_omits_registered(self):
        prereg_schema = RegistrationSchema.objects.get(name='Prereg Challenge', schema_version=2)

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
        d1.registered_node = factories.RegistrationFactory()
        d1.save()
        drafts = drafts_for_user(self.user, 'prereg')
        for d in drafts:
            assert_in(d._id, (d2._id, d3._id))
            assert_not_equal(d._id, d1._id)


class TestPreregUtils(OsfTestCase):

    def setUp(self):
        super(TestPreregUtils, self).setUp()

    def test_get_prereg_schema_returns_prereg_metaschema(self):
        schema = get_prereg_schema()
        assert_is_instance(schema, RegistrationSchema)
        assert_equal(schema.name, 'Prereg Challenge')

    def test_get_prereg_schema_raises_error_for_invalid_campaign(self):
        with assert_raises(ValueError):
            get_prereg_schema(campaign='invalid')
