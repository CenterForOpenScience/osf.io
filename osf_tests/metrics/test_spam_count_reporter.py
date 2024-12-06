import pytest
from datetime import datetime
from osf.metrics.reporters.private_spam_metrics import PrivateSpamMetricsReporter
from osf.metrics.utils import YearMonth
from osf_tests.factories import NodeLogFactory, NodeFactory
from unittest.mock import patch

@pytest.mark.django_db
def test_private_spam_metrics_reporter():
    start_date = datetime(2024, 10, 1)

    oopspam_node = NodeFactory(spam_data={'who_flagged': 'oopspam'})
    akismet_node = NodeFactory(spam_data={'who_flagged': 'akismet'})

    NodeLogFactory.create_batch(10, action='flag_spam', created=start_date, node=oopspam_node)
    NodeLogFactory.create_batch(5, action='confirm_ham', created=start_date, node=oopspam_node)
    NodeLogFactory.create_batch(20, action='flag_spam', created=start_date, node=akismet_node)
    NodeLogFactory.create_batch(10, action='confirm_ham', created=start_date, node=akismet_node)

    report_yearmonth = YearMonth(2024, 10)

    with patch('osf.external.oopspam.client.OOPSpamClient.get_flagged_count') as mock_oopspam_get_flagged_count, \
         patch('osf.external.oopspam.client.OOPSpamClient.get_hammed_count') as mock_oopspam_get_hammed_count, \
         patch('osf.external.askismet.client.AkismetClient.get_flagged_count') as mock_akismet_get_flagged_count, \
         patch('osf.external.askismet.client.AkismetClient.get_hammed_count') as mock_akismet_get_hammed_count:

        mock_oopspam_get_flagged_count.return_value = 10
        mock_oopspam_get_hammed_count.return_value = 5
        mock_akismet_get_flagged_count.return_value = 20
        mock_akismet_get_hammed_count.return_value = 10

        reporter = PrivateSpamMetricsReporter(report_yearmonth)
        report = reporter.report()

        assert report.node_oopspam_flagged == 10, f"Expected 10, got {report.node_oopspam_flagged}"
        assert report.node_oopspam_hammed == 5, f"Expected 5, got {report.node_oopspam_hammed}"
        assert report.node_akismet_flagged == 20, f"Expected 20, got {report.node_akismet_flagged}"
        assert report.node_akismet_hammed == 10, f"Expected 10, got {report.node_akismet_hammed}"
