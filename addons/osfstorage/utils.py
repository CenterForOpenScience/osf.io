import os
from rest_framework import status as http_status
import logging
import functools

from osf.exceptions import ValidationValueError
from framework.exceptions import HTTPError
from framework.analytics import update_counter
from framework.celery_tasks import app
from framework.postcommit_tasks.handlers import enqueue_postcommit_task
from framework.sessions import get_session
from osf.models import BaseFileNode, Guid

from addons.osfstorage import settings

logger = logging.getLogger(__name__)
LOCATION_KEYS = ['service', settings.WATERBUTLER_RESOURCE, 'object']

def enqueue_update_analytics(node, file, version_idx, action='download'):
    enqueue_postcommit_task(update_analytics_async, (node._id, file._id, version_idx, get_session().session_key, action), {}, celery=True)

@app.task(max_retries=5, default_retry_delay=60)
def update_analytics_async(node_id, file_id, version_idx, session_key=None, action='download'):
    node = Guid.load(node_id).referent
    file = BaseFileNode.load(file_id)
    update_analytics(node, file, version_idx, session_key, action)

def update_analytics(node, file, version_idx, session_key, action='download'):
    """
    :param Node node: Root node to update
    :param str file_id: The _id field of a filenode
    :param int version_idx: Zero-based version index
    :param str action: is this logged as download or a view
    """
    # Pass in contributors and group members to check that their downloads
    # do not count towards total download count
    contributors = []
    if getattr(node, 'contributors_and_group_members', None):
        contributors = node.contributors_and_group_members
    elif getattr(node, 'contributors', None):
        contributors = node.contributors

    node_info = {
        'contributors': contributors
    }
    resource = node.guids.first()

    update_counter(resource, file, version=None, action=action, node_info=node_info, session_key=session_key)
    update_counter(resource, file, version_idx, action, node_info=node_info, session_key=session_key)


def serialize_revision(node, record, version, index, anon=False):
    """Serialize revision for use in revisions table.

    :param Node node: Root node
    :param FileRecord record: Root file record
    :param FileVersion version: The version to serialize
    :param int index: One-based index of version
    """
    if anon:
        user = None
    else:
        user = {
            'name': version.creator.fullname,
            'url': version.creator.url,
        }

    return {
        'user': user,
        'index': index + 1,
        'date': version.created.isoformat(),
        'downloads': version._download_count if hasattr(version, '_download_count') else record.get_download_count(version=index),
        'md5': version.metadata.get('md5'),
        'sha256': version.metadata.get('sha256'),
    }


SIGNED_REQUEST_ERROR = HTTPError(
    http_status.HTTP_503_SERVICE_UNAVAILABLE,
    data={
        'message_short': 'Upload service unavailable',
        'message_long': (
            'Upload service is not available; please retry '
            'your upload in a moment'
        ),
    },
)


def get_filename(version_idx, file_version, file_record):
    """Build name for downloaded file, appending version date if not latest.

    :param int version_idx: One-based version index
    :param FileVersion file_version: Version to name
    :param FileRecord file_record: Root file object
    """
    if version_idx == len(file_record.versions):
        return file_record.name
    name, ext = os.path.splitext(file_record.name)
    return f'{name}-{file_version.created.isoformat()}{ext}'


def validate_location(value):
    for key in LOCATION_KEYS:
        if key not in value:
            raise ValidationValueError


def must_be(_type):
    """A small decorator factory for OsfStorageFileNode. Acts as a poor mans
    polymorphic inheritance, ensures that the given instance is of "kind" folder or file
    """
    def _must_be(func):
        @functools.wraps(func)
        def wrapped(self, *args, **kwargs):
            if not self.kind == _type:
                raise ValueError(f'This instance is not a {_type}')
            return func(self, *args, **kwargs)
        return wrapped
    return _must_be
