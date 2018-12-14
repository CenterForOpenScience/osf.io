import datetime

from osf_tests.factories import PreprintFactory, PreprintProviderFactory
from osf.models import Preprint
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
    return PreprintFactory._build(Preprint, provider=preprint_provider)


@pytest.fixture()
def right_before_my_birthday():
    return {'run_date': datetime.datetime(year=1991, month=9, day=25, hour=23, minute=59, second=59, tzinfo=pytz.utc),
            'preprint_date_created': datetime.datetime(year=1991, month=9, day=25, hour=22, minute=59, second=59, tzinfo=pytz.utc)
            }

@pytest.fixture()
def my_birthday_at_midnight():
    return {'run_date': datetime.datetime(year=1991, month=9, day=25, hour=0, tzinfo=pytz.utc),
            'preprint_date_created': datetime.datetime(year=1991, month=9, day=24, hour=23, tzinfo=pytz.utc)
            }

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('date', [right_before_my_birthday(), my_birthday_at_midnight()])
class TestPreprintCount:

    def test_get_preprint_count(self, preprint, date):

        requests.post = mock.MagicMock()
        resp = requests.Response()
        resp._content = '{"hits" : {"total" : 1}}'
        requests.post.return_value = resp

        field = Preprint._meta.get_field('created')
        field.auto_now_add = False  # We have to fudge the time because Keen doesn't allow same day queries.

        preprint.created = date['preprint_date_created']
        preprint.save()

        field.auto_now_add = True
        results = PreprintSummary().get_events(date['run_date'].date())

        assert len(results) == 1

        data = results[0]
        assert data['provider']['name'] == 'Test 1'
        assert data['provider']['total'] == 1
