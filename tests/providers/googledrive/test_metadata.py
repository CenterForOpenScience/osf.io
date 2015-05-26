import pytest

import os
from urllib.parse import quote

from waterbutler.providers.googledrive.provider import GoogleDrivePath
from waterbutler.providers.googledrive.provider import GoogleDrivePathPart
from waterbutler.providers.googledrive.metadata import GoogleDriveRevision
from waterbutler.providers.googledrive.metadata import GoogleDriveFileMetadata
from waterbutler.providers.googledrive.metadata import GoogleDriveFolderMetadata

from tests.providers.googledrive import fixtures


@pytest.fixture
def basepath():
    return GoogleDrivePath('/conrad')


def test_file_metadata_drive(basepath):
    item = fixtures.list_file['items'][0]
    path = basepath.child(item['title'])
    parsed = GoogleDriveFileMetadata(item, path)

    assert parsed.provider == 'googledrive'
    assert parsed.id == item['id']
    assert path.name == item['title']
    assert parsed.name == item['title']
    assert parsed.size == item['fileSize']
    assert parsed.modified == item['modifiedDate']
    assert parsed.content_type == item['mimeType']
    assert parsed.extra == {'revisionId': item['version']}
    assert parsed.path == '/' + os.path.join(*[x.raw for x in path.parts])
    assert parsed.materialized_path == str(path)


def test_file_metadata_drive_slashes(basepath):
    item = fixtures.file_forward_slash
    path = basepath.child(item['title'])
    parsed = GoogleDriveFileMetadata(item, path)

    assert parsed.provider == 'googledrive'
    assert parsed.id == item['id']
    assert parsed.name == item['title']
    assert parsed.name == path.name
    assert parsed.size == item['fileSize']
    assert parsed.modified == item['modifiedDate']
    assert parsed.content_type == item['mimeType']
    assert parsed.extra == {'revisionId': item['version']}
    assert parsed.path == '/' + os.path.join(*[x.raw for x in path.parts])
    assert parsed.materialized_path == str(path)


def test_file_metadata_docs(basepath):
    item = fixtures.docs_file_metadata
    path = basepath.child(item['title'])
    parsed = GoogleDriveFileMetadata(item, path)

    assert parsed.name == item['title'] + '.gdoc'
    assert parsed.extra == {'revisionId': item['version'], 'downloadExt': '.docx'}


def test_folder_metadata():
    item = fixtures.folder_metadata
    path = GoogleDrivePath('/we/love/you/conrad').child(item['title'], folder=True)
    parsed = GoogleDriveFolderMetadata(item, path)

    assert parsed.provider == 'googledrive'
    assert parsed.id == item['id']
    assert parsed.name == item['title']
    assert parsed.extra == {'revisionId': item['version']}
    assert parsed.path == '/' + os.path.join(*[x.raw for x in path.parts]) + '/'
    assert parsed.materialized_path == str(path)


def test_folder_metadata_slash():
    item = fixtures.folder_metadata_forward_slash
    path = GoogleDrivePath('/we/love/you/conrad').child(item['title'], folder=True)
    parsed = GoogleDriveFolderMetadata(item, path)

    assert parsed.provider == 'googledrive'
    assert parsed.id == item['id']
    assert parsed.name == item['title']
    assert parsed.extra == {'revisionId': item['version']}
    assert parsed.path == '/' + os.path.join(*[x.raw for x in path.parts]) + '/'
    assert parsed.materialized_path == str(path)


def test_revision_metadata():
    item = fixtures.revision_metadata
    parsed = GoogleDriveRevision(item)
    assert parsed.version_identifier == 'revision'
    assert parsed.version == item['id']
    assert parsed.modified == item['modifiedDate']
