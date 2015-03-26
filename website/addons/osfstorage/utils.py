# -*- coding: utf-8 -*-

import os
import httplib
import logging
import functools


from modularodm.exceptions import NoResultsFound
from modularodm.exceptions import ValidationValueError
from modularodm.storage.base import KeyExistsException

from framework.exceptions import HTTPError
from framework.analytics import update_counter

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


def update_analytics(node, path, version_idx):
    """
    :param Node node: Root node to update
    :param str path: Path to file
    :param int version_idx: One-based version index
    """
    update_counter(u'download:{0}:{1}'.format(node._id, path))
    update_counter(u'download:{0}:{1}:{2}'.format(node._id, path, version_idx))


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


def copy_files(src, target_settings, parent=None):
    cloned = src.clone()
    cloned.parent = parent
    cloned.node_settings = target_settings

    if src.is_file:
        cloned.versions = src.versions

    cloned.save()

    if src.is_folder:
        for child in src.children:
            copy_files(child, target_settings, parent=cloned)

    return cloned
