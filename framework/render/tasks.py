# -*- coding: utf-8 -*-

import os
import logging
import errno
import codecs

from framework.tasks import app
from website import settings
from mfr.renderer import FileRenderer
import mfr
from mfr.renderer.exceptions import MFRError
from website.language import ERROR_PREFIX, STATA_VERSION_ERROR, BLANK_OR_CORRUPT_TABLE_ERROR


logger = logging.getLogger(__name__)

config = {}
FileRenderer.STATIC_PATH = '/static/mfr'


def ensure_path(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

CUSTOM_ERROR_MESSAGES = {}

# Catch ImportError in case tabular or its dependencies are not installed
try:
    from mfr.renderer.tabular.exceptions import StataVersionError, BlankOrCorruptTableError
    CUSTOM_ERROR_MESSAGES[StataVersionError] = STATA_VERSION_ERROR
    CUSTOM_ERROR_MESSAGES[BlankOrCorruptTableError] = BLANK_OR_CORRUPT_TABLE_ERROR
except ImportError:
    logger.warn('Unable to import tabular module')

# Unable to render. Download the file to view it.
def render_mfr_error(err):
    pre = ERROR_PREFIX
    msg = CUSTOM_ERROR_MESSAGES.get(type(err), err.message)
    return """
           <div class="osf-mfr-error">
           <p>{pre}</p>
           <p>{msg}</p>
           </div>
        """.format(**locals())


@app.task(ignore_result=True, timeout=settings.MFR_TIMEOUT)
def _build_rendered_html(file_path, cache_dir, cache_file_name, download_url):
    """

    :param str file_path: Full path to raw file on disk
    :param str cache_dir: Folder to store cached file in
    :param str cache_file_name: Name of cached file
    :param str download_url: External download URL
    """
    file_pointer = codecs.open(file_path)

    # Build path to cached content
    # Note: Ensures that cache directories have the same owner as the files
    # inside them
    ensure_path(cache_dir)
    cache_file_path = os.path.join(cache_dir, cache_file_name)

    # Render file
    try:
        rendered = mfr.render(file_pointer, url=download_url)
    except MFRError as err:
        rendered = render_mfr_error(err).format(download_path=download_url)

    # Close read pointer
    file_pointer.close()

    # Cache rendered content
    with codecs.open(cache_file_path, 'w', 'utf-8') as write_file_pointer:
        write_file_pointer.write(rendered)

    os.remove(file_path)


def build_rendered_html(file_path, cache_dir, cache_file_name, download_url):
    """Public wrapper for the rendering task.
    """
    args = (file_path, cache_dir, cache_file_name, download_url)
    if settings.USE_CELERY:
        _build_rendered_html.apply_async(args)
    else:
        # Call task synchronously
        _build_rendered_html(*args)
