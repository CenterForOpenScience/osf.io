import re
import hashlib
import logging
import argparse
import requests
import itertools
import collections

from framework.transactions.context import TokuTransaction
from modularodm.query.querydialect import DefaultQueryDialect as Q

from website.app import init_app
from scripts import utils as scripts_utils
from website.files.models.base import FileNode
from website.addons.googledrive.model import GoogleDriveNodeSettings
from website.files.models.googledrive import GoogleDriveFileNode, GoogleDriveFile, GoogleDriveFolder

logger = logging.getLogger(__name__)
base_path_regex = re.compile('[^/]+/?$')
FOLDER_MIME_TYPE = 'application/vnd.google-apps.folder'
all_file_tally = collections.Counter()


def main():
    """We have been identifying GoogleDrive files by path but we want to switch to the unique IDs
    that GoogleDrive assigns to files and folders.  This will let us track file/folder provenance
    across renames, moves, etc.  The WaterButler provider has been updated to do this (thanks,
    @TomBaxter!), and now we need to migrate the existing stored metadata.

    To do so will require using the owner's oauth access token and provider settings, which are
    tracked per-node.  Basic plan is to get all GoogleDriveFileNodes, group them by parent node,
    and batch update per parent node.

    Failure modes:

    If a stored file no longer appears in the list of its putative parent's children, assume it has
    been deleted or moved and that we can no longer track it.  Remove its metadata from the OSF.

    If we try to get the list of children of a parent folder, and Google hands us back a non-200
    response, we'll throw an error and abort.  I'm not sure if there's a case where this is likely
    to happen.  Two possibilities: a user deletes a child folder at the exact time the migration
    is running, between when the child folder is identified and the child folder meta is retreived.
    I suppose if a user has disabled their gdrive addon it might cause an issue, but again,
    doesn't seem likely.

    What happens if the OAuth refresh fails?  This is low probability.  We refresh tokens regularly,
    but it's possible a user could deauth the node during migration.  Kicking down the road for now.

    Other consideration:

    What to do when we find an entry on gdrive that's not in the osf?  We could go ahead and add it.
    However, it'll get added correctly anyway the next time the user hits the NodeFilesList endpoint
    either directly or indirectly (i.e. via fangorn).  I think for now we should report on what we
    find, but not actually add it.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry', action='store_true', help='Do a dry run. Check with gdrive, report on outcome, but do not make changes')
    parser.add_argument('-v', '--verbose', action='count', help="verbosity")
    args = parser.parse_args()

    logger.setLevel(logging.INFO if args.verbose == 1 else logging.DEBUG if args.verbose == 2 else logging.WARNING)
    scripts_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)

    with TokuTransaction():
        current_node = None
        gdrive_filenodes = []
        node_count = 0
        file_count = 0
        for file in GoogleDriveFileNode.find().sort('node'):
            file_count += 1
            if current_node != file.node_id:  # node changed, so update current list then reset
                node_count += 1
                update_node_files(current_node, gdrive_filenodes, args.dry)
                gdrive_filenodes = []
                current_node = file.node_id

            gdrive_filenodes.append(file)

        update_node_files(current_node, gdrive_filenodes, args.dry)  # update final batch
        logger.warning('Found {} files across {} nodes'.format(file_count, node_count))
        logger.warning('  {} were updated, {} were deleted'.format(all_file_tally['updated'], all_file_tally['deleted']))
        logger.warning('  {} files and folders would have been added, if we did that sort of thing.'.format(all_file_tally['created']))


def _build_query(folder_id):
    """Stolen from WaterButler's googledrive provider. Builds a query to get all files/folders that
    are children of `folder_id`.
    """
    queries = [
        "'{}' in parents".format(folder_id),
        'trashed = false',
        "mimeType != 'application/vnd.google-apps.form'",
    ]
    return ' and '.join(queries)


def _response_to_metadata(response, parent):
    """Turn a raw GoogleDrive item representation into a WaterButler-style metadata structure.
    Necessary so that `history` can be updated properly.  `parent` is the materialized path of
    the item's parent folder.  It is needed to construct the item's `materialized_path` property,
    since that is not available from the GoogleDrive representation.

    This code is stolen^Winterpreted from WB's waterbutler/providers/googledrive/metadata.py
    """
    is_folder = response.get('mimeType') == FOLDER_MIME_TYPE
    name = response['title']
    extra = { 'revisionId': response.get('version') }

    # munge google docs, spreadsheets, etc. so they look like their ooxml counterparts
    if not is_folder:
        if is_docs_file(response):
            ext = get_extension(response)
            name += ext
            extra['downloadExt'] = get_download_extension(response)
        extra['webView'] = response.get('alternateLink')

    return {
        'contentType': None if is_folder else response.get('mimeType'),
        'etag': hashlib.sha256('{}::{}'.format('googledrive', response.get('version')).encode('utf-8')).hexdigest(),
        'extra': extra,
        'kind': 'folder' if is_folder else 'file',
        'materialized': parent + name + ('/' if is_folder else ''),
        'modified': response.get('modifiedDate'),
        'name': name,
        'path': '/{}'.format(response.get('id')) + ('/' if is_folder else ''),
        'provider': 'googledrive',
        'size': response.get('fileSize'),
    }


def update_node_files(current_node, gdrive_filenodes, dry=True):
    """Handle updates for all googledrive files belonging to `current_node` in one batch.  Each
    node has its own oauth settings and base folder.  Entity lookup is done most efficiently by
    querying by parent folder, so start by partitioning all files into lists by parent folder.

    E.g. This:

        /foo.txt
        /bar.txt
        /baz/
        /baz/quux.txt

    becomes:

        # parent   children
        [ '/',     [ '/foo.txt', '/bar.txt', '/baz/' ] ],
        [ '/baz/', [ 'quux.txt' ] ],

    Next, for each list query by the parent folder, and update each item in the list from the
    response.  Tricky: when we begin, we only have access to the id of the root folder.  Fix: sort
    folders by full path, parents will always come before children.  When we encounter a folder,
    save its id to the dict of parent folders, so that we'll be able to build a query for its
    children.

    When we get back the children list, turn them from GDrive item representations to WB-style
    metadata. For each file, find its corresponding metadata and update it with the new id.  If we
    can't find it, trash it.
    """
    if current_node is None:  # gag, first call is always this
        return

    node_settings = GoogleDriveNodeSettings.find_one(Q('owner', 'eq', current_node))
    access_token = node_settings.fetch_access_token()
    headers = {'authorization': 'Bearer {}'.format(access_token)}
    base_url = 'https://www.googleapis.com/drive/v2/files'

    logger.info(u' Node: {}'.format(current_node))

    parent_folders = { '/': node_settings.folder_id }

    node_file_tally = collections.Counter()

    # how does one do a schwartzian transform in python? each schwartz entry is [root, filenode]
    schwartz = [ [base_path_regex.sub('', x.path), x] for x in gdrive_filenodes ]
    ordered = sorted(schwartz, key=lambda x: x[0])
    for filenode_root, filenodes in itertools.groupby(ordered, lambda x: x[0]):
        logger.debug(u'  Dir: {}'.format(filenode_root))

        payload = {'alt': 'json', 'q':_build_query(parent_folders[filenode_root])}
        resp = requests.get(base_url, params=payload, headers=headers)

        if resp.status_code != 200:
            raise Exception(
                "Not gonna lie, I wasn't expecting this. How did this happen? "
                "I was trying to get a list of child entities of {} for node {}"
                ", but when I asked Google about it, they handed me back a {}"
                " response code.  What the hell, Google, I thought we were tight?!"
                " Oh well, I guess I have no choice but to abort and investigate. "
                "Thumbs down.".format(filenode_root, current_node, resp.status_code)
            )

        items = resp.json()['items']

        metadata = [ _response_to_metadata(item, filenode_root) for item in items ]
        grouped_metadata = {'file': {}, 'folder': {}}
        for metadatum in metadata:
            grouped_metadata[ metadatum['kind'] ][ metadatum['name'] ] = metadatum

        files_ordered = sorted(list(filenodes), key=lambda x: x[1].path)

        root_file_tally = {'updated': 0, 'deleted': 0, 'created': 0}
        for pair in files_ordered:
            storedfilenode = pair[1]
            filenode = GoogleDriveFile(storedfilenode) if storedfilenode.is_file else GoogleDriveFolder(storedfilenode)
            kind = 'file' if filenode.is_file else 'folder'
            logger.debug(u'    File: {}'.format(filenode.path))

            if filenode.name not in grouped_metadata[kind]:
                logger.debug(u'      Action: file not found, deleted.')
                root_file_tally['deleted'] += 1
                if not dry:
                    filenode.delete()
                continue

            found = grouped_metadata[kind].pop(filenode.name)

            if not filenode.is_file:
                parent_folders[filenode.path] = found['path'].strip('/')

            logger.debug(u'      Action: file found, path updated to: {}'.format(found['path']))
            root_file_tally['updated'] += 1
            if not dry:
                filenode.path = found['path']
                filenode.update(found['extra']['revisionId'], found)

        root_file_tally['created'] = len(grouped_metadata['file']) + len(grouped_metadata['folder'])
        logger.debug("    Summary: Updated {} files/folders for dir".format(root_file_tally['updated']))
        logger.debug("    Summary: Deleted {} files/folders for dir".format(root_file_tally['deleted']))
        logger.debug("    Summary: Found {} unrecorded files/folders for dir".format(root_file_tally['created']))
        node_file_tally.update(root_file_tally)

    logger.info("   Summary: Updated {} files/folders for node".format(node_file_tally['updated']))
    logger.info("   Summary: Deleted {} files/folders for node".format(node_file_tally['deleted']))
    logger.info("   Summary: Found {} unrecorded files/folders for node".format(node_file_tally['created']))
    all_file_tally.update(node_file_tally)


### BEGIN STEALING FROM WATERBUTLER's waterbutler/providers/googledrive/utils.py

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

### END OF THEFT


if __name__ == '__main__':
    main()

