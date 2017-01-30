from nose.tools import *  # noqa


from tests.base import OsfTestCase
from website.models import PreprintProvider
from website.project.licenses import ensure_licenses
from scripts.update_taxonomies import main as taxonomy_main
from scripts.populate_preprint_providers import main as populate_main


class TestAddPreprintProviders(OsfTestCase):
    def setUp(self):
        taxonomy_main(warn=False)
        ensure_licenses(warn=False)

    def tearDown(self):
        PreprintProvider.remove()

    def test_add_prod_providers(self):
        populate_main('prod')
        assert_equal(PreprintProvider.find().count(), 4)

    def test_add_default_providers(self):
        populate_main(None)
        assert_equal(PreprintProvider.find().count(), 4)

    def test_add_staging_providers(self):
        populate_main('stage')
        assert_equal(PreprintProvider.find().count(), 6)
