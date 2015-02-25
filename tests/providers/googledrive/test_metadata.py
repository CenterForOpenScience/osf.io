import pytest

import os

from waterbutler.providers.googledrive.metadata import GoogleDriveFileMetadata
from waterbutler.providers.googledrive.metadata import GoogleDriveFolderMetadata
from waterbutler.providers.googledrive.metadata import GoogleDriveRevision

from tests.providers.googledrive import fixtures


def test_file_metadata_drive():
    path = '/conrad'
    item = fixtures.list_file['items'][0]
    parsed = GoogleDriveFileMetadata(item, path)
    assert parsed.provider == 'googledrive'
    assert parsed.id == item['id']
    assert parsed.name == item['title']
    assert parsed.size == item['fileSize']
    assert parsed.modified == item['modifiedDate']
    assert parsed.content_type == item['mimeType']
    assert parsed.path == os.path.join(path, item['title'])
    assert parsed.extra == {'revisionId': item['version']}


def test_file_metadata_docs():
    path = '/conrad'
    item = fixtures.docs_file_metadata
    parsed = GoogleDriveFileMetadata(item, path)
    assert parsed.name == item['title'] + '.gdoc'
    assert parsed.extra == {'revisionId': item['version'], 'downloadExt': '.docx'}


def test_folder_metadata():
    path = '/we/love/you/conrad'
    item = fixtures.folder_metadata
    parsed = GoogleDriveFolderMetadata(item, path)
    assert parsed.provider == 'googledrive'
    assert parsed.id == item['id']
    assert parsed.name == item['title']
    assert parsed.path == os.path.join(path, item['title'] + '/')
    assert parsed.extra == {'revisionId': item['version']}


def test_revision_metadata():
    item = fixtures.revision_metadata
    parsed = GoogleDriveRevision(item)
    assert parsed.version_identifier == 'revision'
    assert parsed.version == item['id']
    assert parsed.modified == item['modifiedDate']
