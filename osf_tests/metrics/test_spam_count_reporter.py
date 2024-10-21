import datetime
import pytest
from osf.metrics.reporters.spam_count import SpamCountReporter
from osf.external.oopspam.client import OOPSpamClient
from osf.external.askismet.client import AkismetClient

@pytest.fixture
def mock_oopspam_client(mocker):
    mock = mocker.patch('osf.external.oopspam.client.OOPSpamClient')
    mock.get_flagged_count.return_value = 10
    mock.get_hammed_count.return_value = 5
    return mock

@pytest.fixture
def mock_akismet_client(mocker):
    mock = mocker.patch('osf.external.askismet.client.AkismetClient')
    mock.get_flagged_count.return_value = 20
    mock.get_hammed_count.return_value = 10
    return mock

@pytest.fixture
def mock_nodelog_model(mocker):
    mock = mocker.patch('osf.models.NodeLog')
    mock.filter.return_value.count.return_value = 100
    return mock

@pytest.fixture
def mock_preprintlog_model(mocker):
    mock = mocker.patch('osf.models.PreprintLog')
    mock.filter.return_value.count.return_value = 50
    return mock

def test_spam_count_reporter(mock_oopspam_client, mock_akismet_client, mock_nodelog_model, mock_preprintlog_model):
    report_month = datetime.datetime(2024, 10, 1)
    reporter = SpamCountReporter()
    report = reporter.report(report_month)

    assert report[0].oopspam_flagged == 10
    assert report[0].oopspam_hammed == 5
    assert report[0].akismet_flagged == 20
    assert report[0].akismet_hammed == 10
    assert report[0].node_confirmed_spam == 100
    assert report[0].preprint_confirmed_spam == 50
