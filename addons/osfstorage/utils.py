# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from rest_framework import status as http_status
import logging
import functools

from osf.exceptions import ValidationValueError
from framework.exceptions import HTTPError
from framework.analytics import update_counter

from addons.osfstorage import settings

logger = logging.getLogger(__name__)
LOCATION_KEYS = ['service', settings.WATERBUTLER_RESOURCE, 'object']


def update_analytics(node, file_id, version_idx, action='download'):
    """
    :param Node node: Root node to update
    :param str file_id: The _id field of a filenode
    :param int version_idx: Zero-based version index
    :param str action: is this logged as download or a view
    """
    # Pass in contributors to check that contributors' downloads
    # do not count towards total download count
    contributors = []
    if node.contributors:
        contributors = node.contributors
    node_info = {
        'contributors': contributors
    }

    update_counter('{0}:{1}:{2}'.format(action, node._id, file_id), node_info=node_info)
    update_counter('{0}:{1}:{2}:{3}'.format(action, node._id, file_id, version_idx), node_info=node_info)


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
    return u'{name}-{date}{ext}'.format(
        name=name,
        date=file_version.created.isoformat(),
        ext=ext,
    )


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
                raise ValueError('This instance is not a {}'.format(_type))
            return func(self, *args, **kwargs)
        return wrapped
    return _must_be


def copy_files(src, target_settings, parent=None, name=None):
    """Copy the files from src to the target nodesettings
    :param OsfStorageFileNode src: The source to copy children from
    :param NodeSettings target_settings: The node settings of the project to copy files to
    :param OsfStorageFileNode parent: The parent of to attach the clone of src to, if applicable
    """
    cloned = src.clone()
    cloned.parent = parent
    cloned.name = name or cloned.name
    cloned.node_settings = target_settings

    if src.is_file:
        cloned.versions = src.versions

    cloned.save()

    if src.is_folder:
        for child in src.children:
            copy_files(child, target_settings, parent=cloned)

    return cloned
