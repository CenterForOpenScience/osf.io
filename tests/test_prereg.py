from nose.tools import *

from website.prereg import prereg_landing_page as landing_page
from website.project.model import ensure_schemas

from tests.base import OsfTestCase
from tests import factories


class PreregLandingPageTestCase(OsfTestCase):
    def setUp(self):
        super(PreregLandingPageTestCase, self).setUp()
        self.user = factories.UserFactory()

    def test_no_projects(self):
        assert_equal(
            landing_page(user=self.user),
            {
                'has_project': False,
                'has_draft_registration': False,
            }
        )

    def test_has_project(self):
        factories.ProjectFactory(creator=self.user)

        assert_equal(
            landing_page(user=self.user),
            {
                'has_project': True,
                'has_draft_registration': False,
            }
        )

    def test_has_project_and_draft_registration(self):
        ensure_schemas()
        factories.DraftRegistrationFactory(initiator=self.user)

        assert_equal(
            landing_page(user=self.user),
            {
                'has_project': True,
                'has_draft_registration': True,
            }
        )
