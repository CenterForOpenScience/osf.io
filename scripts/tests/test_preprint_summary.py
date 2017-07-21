import datetime

from tests.base import OsfTestCase
from osf_tests.factories import PreprintFactory, PreprintProviderFactory
from osf.models import PreprintService
from nose.tools import *  # PEP8 asserts
from django.utils import timezone

from scripts.analytics.preprint_summary import PreprintSummary



class TestPreprintCount(OsfTestCase):

    def setUp(self):
        super(TestPreprintCount, self).setUp()
        field = PreprintService._meta.get_field('date_created')
        field.auto_now_add = False  # We have to fudge the time because Keen doesn't allow same day queries.

        self.preprint_provider = PreprintProviderFactory(name='Test 1')
        self.preprint = PreprintFactory._build(PreprintService, provider=self.preprint_provider)

        self.date = datetime.datetime.utcnow() - datetime.timedelta(1)
        self.preprint.date_created = self.date - datetime.timedelta(0.1)
        self.preprint.save()

        field.auto_now_add = True
        self.results = PreprintSummary().get_events(self.date.date())

    def test_get_preprint_count(self):

        assert_equal(len(self.results), 1)

        data = self.results[0]
        assert_equal(data['provider']['name'], 'Test 1')
        assert_equal(data['provider']['total'], 1)

