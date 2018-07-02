# encoding: utf-8
import mock
import pytest
import pytz
import datetime

from django.utils import timezone

from addons.osfstorage import utils
from addons.osfstorage.tests.utils import StorageTestCase

from osf_tests.factories import ProjectFactory

from scripts.analytics.download_count_summary import DownloadCountSummary


@pytest.mark.django_db
class TestDownloadCount(StorageTestCase):

    def test_download_count(self):
        # Keen does not allow same day requests so we have to do some time traveling to my birthday
        timezone.now = mock.Mock(return_value=datetime.datetime(1991, 9, 25).replace(tzinfo=pytz.utc))
        node = ProjectFactory()

        utils.update_analytics(node, 'fake id', {'contributors': node.contributors})

        # Now back to the future, querying old date.
        timezone.now = mock.Mock(return_value=datetime.datetime.now().replace(tzinfo=pytz.utc))
        query_date = datetime.date(1991, 9, 25)

        event = DownloadCountSummary().get_events(query_date)

        assert event[0]['files']['total'] == 1
