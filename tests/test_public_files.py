from nose.tools import *  # flake8: noqa
from tests.base import OsfTestCase
from tests.factories import InstitutionFactory

from website.models import Node
from website.project import new_public_files_collection

class TestPublicFiles(OsfTestCase):
    self.public_files
    def setUp(self):
        super(TestPublicFiles, self).setUp()

        self.title = str(randint(1, 20000))
        self.public_files = Node(
                    title= self.title,
                    creator=user,
                    category='project',
                    is_public=True,
                    is_public_files_collection=True,
                )
        self.public_files.save()

    def test_file_upload:
        pass

    def test_all_file_uploads_public:
        pass

    def test_file_uploaded_is_correct_file:
        pass

    def test_for_search:
        from website.search.search import search
        from website.search.util import build_query
        results = search(build_query('is_public_files_collection'))['results']
        assert_equal(len(results), 0)


    def tearDown(self):
        super(TestPublicFiles, self).tearDown()
        self.public_files.remove()
