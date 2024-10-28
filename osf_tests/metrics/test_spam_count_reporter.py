import pytest
from datetime import datetime
from osf.metrics.reporters.spam_count import SpamCountReporter
from unittest import mock
from osf.metrics.utils import YearMonth
from osf_tests.factories import NodeLogFactory, NodeFactory

@pytest.fixture
def mock_oopspam_client():
    with mock.patch('osf.external.oopspam.client.OOPSpamClient') as mock_client:
        instance = mock_client.return_value
        instance.get_flagged_count.return_value = 10
        instance.get_hammed_count.return_value = 5
        yield instance

@pytest.fixture
def mock_akismet_client():
    with mock.patch('osf.external.askismet.client.AkismetClient') as mock_client:
        instance = mock_client.return_value
        instance.get_flagged_count.return_value = 20
        instance.get_hammed_count.return_value = 10
        yield instance

@pytest.mark.django_db
def test_spam_count_reporter():
    start_date = datetime(2024, 10, 1)

    oopspam_node = NodeFactory(spam_data={'who_flagged': 'oopspam'})
    akismet_node = NodeFactory(spam_data={'who_flagged': 'akismet'})

    NodeLogFactory.create_batch(10, action='flag_spam', created=start_date, node=oopspam_node)
    NodeLogFactory.create_batch(5, action='confirm_ham', created=start_date, node=oopspam_node)
    NodeLogFactory.create_batch(20, action='flag_spam', created=start_date, node=akismet_node)
    NodeLogFactory.create_batch(10, action='confirm_ham', created=start_date, node=akismet_node)

    report_yearmonth = YearMonth(2024, 10)
    reporter = SpamCountReporter()
    report = reporter.report(report_yearmonth)

    assert report[0].oopspam_flagged == 10
    assert report[0].oopspam_hammed == 5
    assert report[0].akismet_flagged == 20
    assert report[0].akismet_hammed == 10
