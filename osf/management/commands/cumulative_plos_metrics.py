import csv
import logging
import requests
import tempfile

from requests_oauthlib import OAuth2

from osf.metrics import PreprintView, PreprintDownload
from osf.utils.fields import ensure_str
from website.settings import (
    PLOS_METRICS_BASE_FOLDER,
    PLOS_METRICS_INITIAL_FILE_DOWNLOAD_URL,
    PLOS_METRICS_OSF_TOKEN,
)


DEFAULT_API_VERSION = '2.20'
TEMP_FOLDER = tempfile.mkdtemp(suffix='/')
COL_HEADERS = [
    'id',
    'doi',
    'link',
    'guid',
    'type',
    'views',
    'downloads',
]

logger = logging.getLogger(__name__)

def bearer_token_auth(token):
    token_dict = {
        'token_type': 'Bearer',
        'access_token': token
    }
    return OAuth2(token=token_dict)

def upload_metrics_file(file_path, params):
    with open(file_path, 'rb') as metrics_file:
        requests.put(
            url=PLOS_METRICS_BASE_FOLDER,
            headers={'Accept': f'application/vnd.api+json;version={DEFAULT_API_VERSION}'},
            params=params,
            data=metrics_file,
            auth=bearer_token_auth(PLOS_METRICS_OSF_TOKEN),
        )

def parse_base_file():
    r = requests.get(
        url=PLOS_METRICS_INITIAL_FILE_DOWNLOAD_URL,
        headers={'Content-type': 'application/CSV'},
        auth=bearer_token_auth(PLOS_METRICS_OSF_TOKEN)
    )
    csvr = csv.DictReader(ensure_str(r.content).splitlines())
    assert csvr.fieldnames == COL_HEADERS, f'Unexpected headers: expected {COL_HEADERS}, got {csvr.fieldnames}'
    return csvr


def fetch_preprint_metric_data(preprint):
    """return: tuple(<view count>, <download count>)
    """
    views = PreprintView.get_count_for_preprint(preprint)
    downs = PreprintDownload.get_count_for_preprint(preprint)
    return views, downs

def fetch_file_metric_data(file_):
    """return: tuple(<view count>, <download count>)
    """
    views = file_.get_view_count()
    downs = file_.get_download_count()
    return views, downs
