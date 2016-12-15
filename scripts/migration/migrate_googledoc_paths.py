# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import sys
import json
import logging
import argparse

from modularodm import Q
from modularodm import exceptions

from website.app import init_app
from website.files import models
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

GDOC_MIME_PREFIX = 'application/vnd.google-apps'

EXTENSION_FOR = {
    # .gdoc
    'application/vnd.google-apps.document': 'gdoc',
    'application/vnd.google-apps.kix': 'gdoc',

    # .gsheet
    'application/vnd.google-apps.spreadsheet': 'gsheet',
    'application/vnd.google-apps.ritz': 'gsheet',

    # .gslides
    'application/vnd.google-apps.presentation': 'gslides',
    'application/vnd.google-apps.punch': 'gslides',

    # .gdraw
    'application/vnd.google-apps.drawing': 'gdraw',

    # .gmap
    'application/vnd.google-apps.map': 'gmap',

    # .gtable
    'application/vnd.google-apps.fusiontable': 'gtable',

    # .gshortcut
    'application/vnd.google-apps.drive-sdk': 'gshortcut',
}

GDOC_MIME_TYPES = list(EXTENSION_FOR.keys())

HAS_NAME_EXTENSION = ['gdoc', 'gsheet', 'gslides', 'gdraw']

MODELS = [
    ('stored', models.StoredFileNode),
    ('trashed', models.TrashedFileNode),
]


def migrate(reverse=False):
    """For each Googledrive file in StoredFileNode and TrashedFileNode, add an extension to the
    path property if the file is a type of Google Doc.  Determines extension from most recent
    contentType in the metadata history.  If ``reverse`` is true, strips the extension from the
    path instead.
    """
    for model_tuple in MODELS:
        (model_type, model) = model_tuple
        google_files = model.find(
            Q('provider', 'eq', 'googledrive') & Q('is_file', 'eq', True),
        )
        for google_file in google_files:
            logger.debug("Looking at: {} ({})".format(google_file.path, google_file._id))
            if len(google_file.history) == 0:
                continue

            # update the paths for all entries in history
            for history in google_file.history:
                mime_type = history['contentType'].rstrip('0123456789.')  # shortcuts have a /.\d+/ suffix
                if not mime_type.startswith(GDOC_MIME_PREFIX):
                    continue

                if mime_type in GDOC_MIME_TYPES:
                    extension = EXTENSION_FOR[mime_type]
                    orig_history = history['path']
                    if reverse:
                        if history['path'].endswith('.' + extension):
                            history['path'] = history['path'].rsplit('.', 1)[0]
                            history['materialized'] = history['materialized'].rsplit('.', 1)[0]
                    else:
                        history['path'] = '{}.{}'.format(history['path'], extension)
                        history['materialized'] = u'{}.{}'.format(history['materialized'], extension)
                    logger.debug("  History repathed from {} to {}".format(orig_history, history['path']))
                else:
                    logger.debug(
                        "  File history has googleish mime-type but isn't a gdoc?: "
                        "t{}, i{}, n{}".format(mime_type, google_file._id, history['path'])
                    )

            # update path of the Stored or Trashed FileNode to match the last entry in history,
            # IFF the last entry in history is a gdoc.
            mime_type = google_file.history[-1]['contentType'].rstrip('0123456789.')  # shortcuts have a /.\d+/ suffix
            if mime_type.startswith(GDOC_MIME_PREFIX) and mime_type in GDOC_MIME_TYPES:
                orig_path = google_file.path
                google_file.path = google_file.history[-1]['path']
                google_file.materialized_path = google_file.history[-1]['materialized']
                logger.debug("  SFN Repathed from {} to {}".format(orig_path, google_file.path))

            google_file.save()

def audit():
    """Collects and reports statistics about the mime-types and extensions of Googledrive files in
    the StoredFileNode and TrashedFileNode collections.  Also does some sanity checking and reports
    possible inconsistencies in the data.
    """
    tally = {
        'total_files': 0,
        'gdoc_count': 0,
        'gdoc_types': {},
        'mime_types': {},
        'extensions': {},
        'error': {
            'no_history': [],
            'name_mime_mismatch': [],
            'mime_history_change': [],
            'path_history_change': [],
            'path_mime_collision': [],
            'unsupported_mime_type': [],
            'recent_history_mismatch': [],
        }
    }
    for model_tuple in MODELS:
        (model_type, model) = model_tuple
        google_files = model.find(
            Q('provider', 'eq', 'googledrive') & Q('is_file', 'eq', True),
        )
        for google_file in google_files:
            tally['total_files'] += 1

            current_path = google_file.path
            path_ext = _get_extension_from(current_path)
            _tally_extension(tally, 'path', path_ext)

            current_name = google_file.name
            name_ext = _get_extension_from(current_name)
            _tally_extension(tally, 'name', name_ext)

            file_id = '{}|{}'.format(model_type, google_file._id)
            if not len(google_file.history):
                tally['error']['no_history'].append(
                    '{}: has no history. Extensions: path({}), name({})'.format(
                        file_id, path_ext, name_ext,
                    )
                )
                continue

            mime_type = google_file.history[-1]['contentType'] or ''
            tally['mime_types'][mime_type] = tally['mime_types'].get(mime_type, 0) + 1

            # seems to be a gdoc
            if mime_type.startswith(GDOC_MIME_PREFIX):
                tally['gdoc_count'] += 1
                gdoc_type = mime_type.replace(GDOC_MIME_PREFIX + '.', '')
                tally['gdoc_types'][gdoc_type] = tally['gdoc_types'].get(gdoc_type, 0) + 1
                gdoc_ext = EXTENSION_FOR.get(mime_type, None)
                if gdoc_ext is None:
                    tally['error']['unsupported_mime_type'].append(
                        '{}: Unsupported mime_type: {}'.format(file_id, mime_type))
                elif gdoc_ext in HAS_NAME_EXTENSION and gdoc_ext != name_ext:
                    tally['error']['name_mime_mismatch'].append(
                        "{}: mime type ({}) and name type ({}) don't match".format(
                            file_id, mime_type, name_ext))
                    if path_ext is not '':
                        tally['error']['path_mime_collision'].append(
                            "{}: mime extension is ({}) and path extension is ({})".format(
                                file_id, gdoc_ext, path_ext))

            # audit history metadata for changes
            file_history = []
            for history in google_file.history:
                file_history.append([history[x] for x in ('contentType', 'name', 'path')])

                if history['contentType'] != mime_type:
                    tally['error']['mime_history_change'].append(
                        "{}: mime type changed from {} to {}".format(
                            file_id, mime_type, history['contentType']))

                if history['path'] != current_path:
                    tally['error']['path_history_change'].append(
                        "{}: path changed from {} to {}".format(
                            file_id, current_path, history['path']))

            # look for mismatches between recent history and current metadata
            # compare names fully, but only compare path to avoid moves
            if (
                (path_ext != _get_extension_from(google_file.history[-1]['path']))
                or
                (current_name != google_file.history[-1]['name'])
            ):
                tally['error']['recent_history_mismatch'].append({
                    'file_id': file_id,
                    'path': current_path,
                    'name': current_name,
                    'history': file_history,
                })


    print("Tally:\n---")
    print(json.dumps(tally))


def _get_extension_from(filename):
    match = re.search('\.([^.]+)$', filename)
    return match.group(1) if match else ''

def _tally_extension(tally, ext_type, ext):
    if tally['extensions'].get(ext, None) is None:
        tally['extensions'][ext] = {'path': 0, 'name': 0}
    tally['extensions'][ext][ext_type] += 1


def main():
    parser = argparse.ArgumentParser(
        description='Run w/o args for a dry run or with --no-i-mean-it for the real thing.'
    )
    parser.add_argument(
        '--no-i-mean-it',
        action='store_true',
        dest='for_reals',
        help='Run migration and commit changes to db',
    )
    parser.add_argument(
        '--reverse',
        action='store_true',
        dest='reverse',
        help='Run migration in reverse. (e.g. foo.gdoc => foo)',
    )
    parser.add_argument(
        '--audit',
        action='store_true',
        dest='audit',
        help='Collect stats on mime-types and extensions in the db',
    )
    args = parser.parse_args()

    if args.for_reals:
        script_utils.add_file_logger(logger, __file__)

    init_app(set_backends=True, routes=False)
    if args.audit:
        audit()
    else:
        with TokuTransaction():
            migrate(args.reverse)
            if not args.for_reals:
                raise RuntimeError('Dry Run -- Transaction rolled back')


if __name__ == '__main__':
    main()
