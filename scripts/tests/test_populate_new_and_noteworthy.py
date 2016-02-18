import datetime
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from scripts.populate_new_and_noteworthy_projects import main


class TestPopulateNewAndNoteworthy(OsfTestCase):

    def setUp(self):
        super(TestPopulateNewAndNoteworthy, self).setUp()
        self.project = ProjectFactory()
        self.project2 = ProjectFactory()
        self.project3 = ProjectFactory()
        self.project4 = ProjectFactory()
        self.project5 = ProjectFactory()

    def test_migrate_new_and_noteworthy(self):
        main(dry_run=False)
