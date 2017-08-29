import datetime

from osf_tests.factories import PreprintFactory, PreprintProviderFactory
from osf.models import PreprintService
from nose.tools import *  # PEP8 asserts
import mock
import pytest
import pytz
import requests

from scripts.analytics.preprint_summary import PreprintSummary


@pytest.fixture()
def preprint_provider():
    return PreprintProviderFactory(name='Test 1')

@pytest.fixture()
def preprint(preprint_provider):
    return PreprintFactory._build(PreprintService, provider=preprint_provider)

pytestmark = pytest.mark.django_db

class TestPreprintCount:

    def test_get_preprint_count(self, preprint_provider, preprint):

        requests.post = mock.MagicMock()
        resp = requests.Response()
        resp._content = '{"hits" : {"total" : 1}}'
        requests.post.return_value = resp

        field = PreprintService._meta.get_field('date_created')
        field.auto_now_add = False  # We have to fudge the time because Keen doesn't allow same day queries.

        date = datetime.datetime.utcnow() - datetime.timedelta(1)
        preprint.date_created = date - datetime.timedelta(0.1)
        preprint.save()

        field.auto_now_add = True
        results = PreprintSummary().get_events(date.date())

        assert_equal(len(results), 1)

        data = results[0]
        assert_equal(data['provider']['name'], 'Test 1')
        assert_equal(data['provider']['total'], 1)

