from nose.tools import *  # noqa


from tests.base import OsfTestCase
from website.models import PreprintProvider
from scripts.populate_preprint_providers import main


class TestAddPreprintProviders(OsfTestCase):

    def tearDown(self):
        PreprintProvider.remove()

    def test_add_prod_providers(self):
        main('prod')
        assert_equal(PreprintProvider.find().count(), 4)

    def test_add_default_providers(self):
        main()
        assert_equal(PreprintProvider.find().count(), 4)

    def test_add_staging_providers(self):
        main('stage')
        assert_equal(PreprintProvider.find().count(), 6)
