from nose.tools import *  # flake8: noqa
from tests.base import OsfTestCase
import tests.factories as factories

from website.share_window.model import ShareWindow
from website.institutions.model import Institution
from website.project.model import Node
from framework.auth.core import User
from tests.factories import InstitutionFactory

from modularodm import Q
from modularodm.exceptions import NoResultsFound

class TestShareWindow(OsfTestCase):
    def setUp(self):
        super(TestShareWindow, self).setUp()
        self.user = factories.AuthUserFactory()
        self.node = factories.NodeFactory(creator=self.user)

    def tearDown(self):
        super(TestShareWindow, self).tearDown()
        Node.remove()
        User.remove()

    def test_create_share_window(self):
        shareWindow = ShareWindow(self.user)
        assert(shareWindow._id == self.user._id)

    def test_share_window_created_on_register(self):
        self.user.register(self.user.username)
        shareWindow = ShareWindow.load(self.user._id)
        assert(shareWindow.share_window_id == self.user._id)

    def test_share_window_is_public(self):
        ShareWindow().create(self.user)
        shareWindow = ShareWindow.load(self.user._id)
        assert shareWindow.is_public

    def test_share_window_finding(self):

        shareWindow = ShareWindow().create(self.user)
        query = Q('share_window_id', 'eq', shareWindow.share_window_id)
        self.assertRaises(NoResultsFound, Node.find_one, query)

        assert Node.find_one(Q('share_window_id', 'eq', shareWindow.share_window_id), allow_share_windows=True) == shareWindow

    def test_share_window_load(self):

        shareWindow = ShareWindow().create(self.user)
        shareWindowLoaded = shareWindow.load(self.user._id)

        assert shareWindow.share_window_id == shareWindowLoaded.share_window_id

    def test_o(self):
        institution = InstitutionFactory()
        institution.save()

        assert Node.find_one(Q('institution_id', 'eq', institution.institution_id), allow_institution=True)

