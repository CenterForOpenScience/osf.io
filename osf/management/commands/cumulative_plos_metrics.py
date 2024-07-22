import csv
import io
from datetime import datetime
import logging
import requests
import tempfile

from django.core.management.base import BaseCommand
from keen import KeenClient
from requests_oauthlib import OAuth2

from addons.osfstorage.models import OsfStorageFile
from framework.celery_tasks import app as celery_app
from osf.metrics import PreprintView, PreprintDownload
from osf.models import Guid, Node, OSFUser, Preprint, \
    Registration, TrashedFile
from osf.utils.fields import ensure_str
from website.settings import (
    KEEN,
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

keen_client = None
keen_project = KEEN['public']['project_id']
keen_key = KEEN['public']['read_key']
if keen_project and keen_key:
    keen_client = KeenClient(
        project_id=keen_project,
        read_key=keen_key
    )

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

def fetch_metric_data_by_guid(guid):
    """return: tuple(<type>, tuple(<view count>, <download count>))
    """
    g = Guid.load(guid)
    if not g:
        logger.error(f'Unable to find Guid {guid}')
        return None, (0, 0)
    obj = Guid.load(guid).referent
    if isinstance(obj, Node):
        return 'node', fetch_node_metric_data(obj)
    elif isinstance(obj, Registration):
        return 'registration', fetch_node_metric_data(obj)
    elif isinstance(obj, Preprint):
        return 'preprint', fetch_preprint_metric_data(obj)
    elif isinstance(obj, OsfStorageFile):
        return 'file', fetch_file_metric_data(obj)
    elif isinstance(obj, TrashedFile):
        return 'trashedfile', fetch_file_metric_data(obj)
    elif isinstance(obj, OSFUser):
        return 'user', (0, 0)
    else:
        logger.error(f'Unknown type for {guid}')
        return 'Unknown', (0, 0)

def fetch_node_metric_data(node):
    """return: tuple(<view count>, <download count>)
    """
    views = keen_client.count(
        f'pageviews-{node._id[0]}',
        timeframe='this_20_years',
        filters=[{
            'property_name': 'node.id',
            'operator': 'eq',
            'property_value': node._id
        }]
    )
    downs = 0  # AbstractNodes do not download
    return views, downs


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

@celery_app.task(name='osf.management.commands.cumulative_plos_metrics')
def cumulative_plos_metrics():
    today = datetime.today()
    file_name = f'{today.year}_{today.month}_{today.day}_PLOS_Metrics.csv'
    file_path = f'{TEMP_FOLDER}{file_name}'
    logger.info('Parsing initial file...')
    init_data_iter = parse_base_file()
    output = io.StringIO()
    writer = csv.DictWriter(output, COL_HEADERS)
    writer.writeheader()
    logger.info('Gathering data...')
    for r in init_data_iter:
        r['type'], (r['views'], r['downloads']) = fetch_metric_data_by_guid(r['guid'])
        writer.writerow(r)
    params = {
        'kind': 'file',
        'name': file_name
    }
    logger.info('Writing data...')
    with open(file_path, 'w') as writeFile:
        writeFile.write(output.getvalue())
    logger.info('Uploading file...')
    upload_metrics_file(file_path=file_path, params=params)
    logger.info('Done.')


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        start_time = datetime.now()
        logger.info(f'Script start time: {start_time}')
        cumulative_plos_metrics()
        end_time = datetime.now()
        logger.info(f'Script end time: {end_time}')
