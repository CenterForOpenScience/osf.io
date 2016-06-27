from nose.tools import *  # flake8: noqa
from tests.base import OsfTestCase
from tests.factories import UserFactory

from website.models import Node
from website.project import new_public_files_collection

class TestPublicFiles(OsfTestCase):

    def setUp(self):
        super(TestPublicFiles, self).setUp()
        self.user = UserFactory()
        self.public_files = new_public_files_collection(self.user)
        self.public_files.save()

    def test_merge_nodes(self):
        user2 = UserFactory()
        new_public_files_collection(user2)

        self.public_files_collection.merge_public_files(user2.public_files_node)



    def tearDown(self):
        super(TestPublicFiles, self).tearDown()
        self.public_files.remove()
