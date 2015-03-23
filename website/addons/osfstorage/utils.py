# -*- coding: utf-8 -*-

import os
import httplib
import logging
import functools

from modularodm.exceptions import NoResultsFound
from modularodm.exceptions import ValidationValueError
from modularodm.storage.base import KeyExistsException

from framework.exceptions import HTTPError
from website.addons.osfstorage import settings


logger = logging.getLogger(__name__)
LOCATION_KEYS = ['service', settings.WATERBUTLER_RESOURCE, 'object']


def handle_odm_errors(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NoResultsFound:
            raise HTTPError(httplib.NOT_FOUND)
        except KeyExistsException:
            raise HTTPError(httplib.CONFLICT)
    return wrapped


def serialize_metadata(item):
    """Build Treebeard JSON for folder or file.

    :param item: `FileTree` or `FileRecord` to serialize
    """
    return {
        'path': item.path,
        'name': item.name,
        'kind': item.kind,
        'version': len(item.versions),
        'downloads': item.get_download_count(),
    }


def serialize_revision(node, record, version, index):
    """Serialize revision for use in revisions table.

    :param Node node: Root node
    :param FileRecord record: Root file record
    :param FileVersion version: The version to serialize
    :param int index: One-based index of version
    """
    return {
        'index': index + 1,
        'user': {
            'name': version.creator.fullname,
            'url': version.creator.url,
        },
        'date': version.date_created.isoformat(),
        'downloads': record.get_download_count(version=index),
    }


SIGNED_REQUEST_ERROR = HTTPError(
    httplib.SERVICE_UNAVAILABLE,
    data={
        'message_short': 'Upload service unavailable',
        'message_long': (
            'Upload service is not available; please retry '
            'your upload in a moment'
        ),
    },
)


def patch_url(url, **kwargs):
    parsed = furl.furl(url)
    for key, value in kwargs.iteritems():
        setattr(parsed, key, value)
    return parsed.url


def ensure_domain(url):
    return patch_url(url, host=site_settings.DOMAIN)


def build_callback_urls(node, path):
    start_url = node.api_url_for('osf_storage_upload_start_hook', path=path)
    finish_url = node.api_url_for('osf_storage_upload_finish_hook', path=path)
    cached_url = node.api_url_for('osf_storage_upload_cached_hook', path=path)
    ping_url = node.api_url_for('osf_storage_upload_ping_hook', path=path)
    archive_url = node.api_url_for('osf_storage_upload_archived_hook', path=path)
    return {
        'startUrl': ensure_domain(start_url),
        'finishUrl': ensure_domain(finish_url),
        'cachedUrl': ensure_domain(cached_url),
        'pingUrl': ensure_domain(ping_url),
        'archiveUrl': ensure_domain(archive_url),
    }


def get_filename(version_idx, file_version, file_record):
    """Build name for downloaded file, appending version date if not latest.

    :param int version_idx: One-based version index
    :param FileVersion file_version: Version to name
    :param FileRecord file_record: Root file object
    """
    if version_idx == len(file_record.versions):
        return file_record.name
    name, ext = os.path.splitext(file_record.name)
    return u'{name}-{date}{ext}'.format(
        name=name,
        date=file_version.date_created.isoformat(),
        ext=ext,
    )


def validate_location(value):
    for key in LOCATION_KEYS:
        if key not in value:
            raise ValidationValueError


def must_be(_type):
    def _must_be(func):
        @functools.wraps(func)
        def wrapped(self, *args, **kwargs):
            if not self.kind == _type:
                raise ValueError('This instance is not a {}'.format(_type))
            return func(self, *args, **kwargs)
        return wrapped
    return _must_be


def copy_files(file_node, node_settings, parent=None):
    cloned = file_node.clone()
    cloned.node_settings = node_settings
    cloned.parent = parent
    cloned.save()
    for child in file_node.children:
        copy_files(child, node_settings, parent=cloned)
    return cloned
