import logging
from nose.tools import *  # noqa


from tests.base import OsfTestCase
from website.models import PreprintProvider
from website.project.licenses import ensure_licenses
from scripts.update_taxonomies import main as taxonomy_main
from scripts.populate_preprint_providers import main as populate_main
from scripts.populate_preprint_providers import STAGING_PREPRINT_PROVIDERS, PROD_PREPRINT_PROVIDERS



class TestAddPreprintProviders(OsfTestCase):
    def setUp(self):
        logger = logging.getLogger()
        logger.setLevel(logging.WARNING)
        taxonomy_main()
        ensure_licenses(warn=False)

    def tearDown(self):
        PreprintProvider.remove()

    def test_add_prod_providers(self):
        populate_main('prod')
        providers = PreprintProvider.find()
        assert_equal(providers.count(), len(PROD_PREPRINT_PROVIDERS))
        ids = [provider._id for provider in providers]
        for id in PROD_PREPRINT_PROVIDERS:
            assert_in(id, ids)
        for id in set(STAGING_PREPRINT_PROVIDERS) - set(PROD_PREPRINT_PROVIDERS):
            assert_not_in(id, ids)


    def test_add_default_providers(self):
        populate_main(None)
        providers = PreprintProvider.find()
        assert_equal(providers.count(), len(PROD_PREPRINT_PROVIDERS))
        ids = [provider._id for provider in providers]
        for id in PROD_PREPRINT_PROVIDERS:
            assert_in(id, ids)
        for id in set(STAGING_PREPRINT_PROVIDERS) - set(PROD_PREPRINT_PROVIDERS):
            assert_not_in(id, ids)


    def test_add_staging_providers(self):
        populate_main('stage')
        providers = PreprintProvider.find()
        assert_equal(PreprintProvider.find().count(), len(STAGING_PREPRINT_PROVIDERS))
        ids = [provider._id for provider in providers]
        for id in STAGING_PREPRINT_PROVIDERS:
            assert_in(id, ids)
