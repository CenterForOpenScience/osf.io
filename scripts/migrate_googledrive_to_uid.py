import re
import logging
import requests
from itertools import groupby

from framework.transactions.context import TokuTransaction
from modularodm.query.querydialect import DefaultQueryDialect as Q

from website.app import init_app
from scripts import utils as scripts_utils
from website.files.models.base import FileNode
from website.files.models.googledrive import GoogleDriveFileNode
from website.addons.googledrive.model import GoogleDriveNodeSettings

logger = logging.getLogger(__name__)

regex = re.compile('[^/]+/?$')
FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'

def main():
    with TokuTransaction():

        current_node = None
        gdrive_filenodes = []
        for file in GoogleDriveFileNode.find().sort('node'):
            if current_node != file.node_id:
                update_node(current_node, gdrive_filenodes)
                gdrive_filenodes = []
                current_node = file.node_id

            gdrive_filenodes.append(file)

        update_node(current_node, gdrive_filenodes)


def _build_query(folder_id):
    queries = [
        "'{}' in parents".format(folder_id),
        'trashed = false',
        "mimeType != 'application/vnd.google-apps.form'",
    ]
    return ' and '.join(queries)


def _response_to_metadata(response, parent):
    is_folder = response.get('mimeType') == FOLDER_MIME_TYPE
    name = response['title']

    if not is_folder and is_docs_file(response):
        ext = get_extension(response)
        name += ext

    extra = {
        'revisionId': response.get('version')
    }
    if not is_folder:
        if is_docs_file(response):
            extra['downloadExt'] = get_download_extension(response)
        extra['webView'] = response.get('alternateLink')

    return {
        'kind': 'folder' if is_folder else 'file',
        'contentType': None if is_folder else response.get('mimeType'),
        'name': name,
        'materialized': parent + name + ('/' if is_folder else ''),
        'modified': response.get('modifiedDate'),
        'etag': response.get('version'),
        'provider': 'googledrive',
        'path': '/{}'.format(response.get('id')) + ('/' if is_folder else ''),
        'size': response.get('fileSize'),
        'extra': extra,
    }

def update_node(current_node, gdrive_filenodes):
    if current_node is None:
        return

    node_settings = GoogleDriveNodeSettings.find_one(Q('owner', 'eq', current_node))
    access_token = node_settings.fetch_access_token()
    headers = {'authorization': 'Bearer {}'.format(access_token)}
    base_url = 'https://www.googleapis.com/drive/v2/files'

    logger.info(u'--Node: {}  (token:{})'.format(current_node, access_token))

    parent_folders = { '/': node_settings.folder_id }
    merp = map(lambda x: [regex.sub('', x.path), x], gdrive_filenodes)
    ordered = sorted(list(merp), key=lambda x: x[0])
    for filenode_root, filenodes in groupby(ordered, lambda x: x[0]):
        logger.info(u'  --Root: {}'.format(filenode_root))

        payload = {'alt': 'json', 'q':_build_query(parent_folders[filenode_root])}
        resp = requests.get(base_url, params=payload, headers=headers)
        items = resp.json()['items']

        metadata = map(lambda x: _response_to_metadata(x, filenode_root), items)

        lunch = sorted(list(filenodes), key=lambda x: x[1].path)

        for pair in lunch:
            storedfilenode = pair[1]
            filenode = GoogleDriveFileNode(storedfilenode)

            logger.info(u'    --File: {}'.format(filenode.path))
            found = None
            for metadatum in metadata:
                if metadatum['name'] == filenode.name and (metadatum['kind'] == 'file') == filenode.is_file:
                    found = metadatum
                    break

            if found is None:
                filenode.delete()
                continue

            if not filenode.is_file:
                parent_folders[filenode.path] = found['path'].strip('/')

            filenode.path = found['path']
            filenode.update(found['extra']['revisionId'], found)



### EVERYTHING BELOW THIS COPIED FROM WATERBUTLER's googledrive/utils.py

DOCS_FORMATS = [
    {
        'mime_type': 'application/vnd.google-apps.document',
        'ext': '.gdoc',
        'download_ext': '.docx',
        'type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    },
    {
        'mime_type': 'application/vnd.google-apps.drawing',
        'ext': '.gdraw',
        'download_ext': '.jpg',
        'type': 'image/jpeg',
    },
    {
        'mime_type': 'application/vnd.google-apps.spreadsheet',
        'ext': '.gsheet',
        'download_ext': '.xlsx',
        'type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    },
    {
        'mime_type': 'application/vnd.google-apps.presentation',
        'ext': '.gslides',
        'download_ext': '.pptx',
        'type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    },
]
DOCS_DEFAULT_FORMAT = {
    'ext': '',
    'download_ext': '.pdf',
    'type': 'application/pdf',
}


def is_docs_file(metadata):
    """Only Docs files have the "exportLinks" key."""
    return metadata.get('exportLinks')


def get_format(metadata):
    for format in DOCS_FORMATS:
        if format['mime_type'] == metadata['mimeType']:
            return format
    return DOCS_DEFAULT_FORMAT


def get_extension(metadata):
    format = get_format(metadata)
    return format['ext']


def get_download_extension(metadata):
    format = get_format(metadata)
    return format['download_ext']


def get_export_link(metadata):
    format = get_format(metadata)
    return metadata['exportLinks'][format['type']]

### END of googledrive/utils.py


if __name__ == '__main__':
    scripts_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    main()

