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


def migrate(reverse=False):
    """For each Googledrive file in StoredFileNode and TrashedFileNode, add an extension to the
    path property if the file is a type of Google Doc.  Determines extension from most recent
    contentType in the metadata history.  If ``reverse`` is true, strips the extension from the
    path instead.
    """
    for model in (models.StoredFileNode, models.TrashedFileNode):
        google_files = model.find(
            Q('provider', 'eq', 'googledrive') & Q('is_file', 'eq', True),
        )
        for google_file in google_files:
            logger.debug("Looking at: {} ({})".format(google_file.path, google_file._id))
            if len(google_file.history) == 0:
                continue
            mime_type = google_file.history[-1]['contentType']
            if mime_type.startswith(GDOC_MIME_PREFIX):
                mime_type = mime_type.rstrip('0123456789.')  # shortcuts have a /.\d+/ suffix
                if mime_type in GDOC_MIME_TYPES:
                    extension = EXTENSION_FOR[mime_type]
                    if reverse:
                        if google_file.path.endswith('.' + extension):
                            google_file.path = google_file.path.rsplit('.', 1)[0]
                    else:
                        google_file.path = '{}.{}'.format(google_file.path, extension)
                    google_file.save()
                    logger.debug("  Repathed to: {}".format(google_file.path))
                else:
                    logger.debug("  file with type but not a gdoc?: t{}, i{}, n{}".format(
                        mime_type, google_file._id, google_file.path
                    ))

def audit():
    """Collects and reports statistics about the mime-types and extensions of Googledrive files in
    the StoredFileNode and TrashedFileNode collections.  Also does some sanity checking and reports
    possible inconsistencies in the data.
    """
    tally = {
        'total_files': 0,
        'gdoc_count': 0,
        'mime': {},
        'gdoc': {},
        'path_ext': {},
        'name_ext': {},
        'error': {
            'no_history': [],
            'name_mime_mismatch': [],
            'mime_history_change': [],
            'unsupported_mime_type': [],
        }
    }
    for model in (models.StoredFileNode, models.TrashedFileNode):
        google_files = model.find(
            Q('provider', 'eq', 'googledrive') & Q('is_file', 'eq', True),
        )
        for google_file in google_files:
            tally['total_files'] += 1
            if not len(google_file.history):
                tally['error']['no_history'].append('{}: has no history'.format(google_file._id))
                continue

            mime_type = google_file.history[-1]['contentType'] or ''
            tally['mime'][mime_type] = tally['mime'].get(mime_type, 0) + 1

            path_ext = _get_extension_from(google_file.path)
            tally['path_ext'][path_ext] = tally['path_ext'].get(path_ext, 0) + 1

            name_ext = _get_extension_from(google_file.name)
            tally['name_ext'][name_ext] = tally['name_ext'].get(name_ext, 0) + 1

            if mime_type.startswith(GDOC_MIME_PREFIX):
                tally['gdoc_count'] += 1
                gdoc_type = mime_type.replace(GDOC_MIME_PREFIX + '.', '')
                tally['gdoc'][gdoc_type] = tally['gdoc'].get(gdoc_type, 0) + 1
                gdoc_ext = EXTENSION_FOR.get(mime_type, None)
                if gdoc_ext is None:
                    tally['error']['unsupported_mime_type'].append(
                        '{}: Unsupported mime_type: {}'.format(google_file._id, mime_type))
                elif gdoc_ext in HAS_NAME_EXTENSION and gdoc_ext != name_ext:
                    tally['error']['name_mime_mismatch'].append(
                        "{}: mime type ({}) and name type ({}) don't match".format(
                            google_file._id, mime_type, name_ext))

            for history in google_file.history:
                if history['contentType'] != mime_type:
                    tally['error']['mime_history_change'].append(
                        "{}: mime type changed from {} to {}".format(
                            google_file._id, mime_type, history['contentType']))



    print("Tally:\n---")
    print(json.dumps(tally))


def _get_extension_from(filename):
    match = re.search('\.([^.]+)$', filename)
    return match.group(1) if match else ''


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
