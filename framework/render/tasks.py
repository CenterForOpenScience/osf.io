import logging
import os
import errno
import codecs
from framework.tasks import celery
from website import settings
from mfr.renderer import FileRenderer
import mfr
import tempfile
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

@celery.task(time_limit=settings.MFR_TIMEOUT)
def _build_rendered_html(file_name, file_content, cache_dir, cache_file_name,
                         download_path):
    """

    :param str file_name:
    :param str file_content:
    :param str cache_dir:
    :param str cache_file_name:
    :param str download_path:

    """

    # Open file pointer if no content provided
    if file_content is None:
        file_pointer = codecs.open(file_name)
    # Else create temporary file with content
    else:
        file_pointer = tempfile.NamedTemporaryFile(
            suffix=os.path.splitext(file_name)[1],
        )
        file_pointer.write(file_content)
        file_pointer.seek(0)

    # Build path to cached content
    # Note: Ensures that cache directories have the same owner as the files
    # inside them
    ensure_path(cache_dir)
    cache_file_path = os.path.join(cache_dir, cache_file_name)

    # Render file
    try:
        rendered = mfr.render(file_pointer, url=download_path)
    except MFRError as err:
        rendered = render_mfr_error(err).format(download_path=download_path)

    # Close read pointer
    file_pointer.close()

    # Cache rendered content
    with codecs.open(cache_file_path, 'w', 'utf-8') as write_file_pointer:
        write_file_pointer.write(rendered)

    return True

# Expose render function
build_rendered_html = _build_rendered_html
if settings.USE_CELERY:
    build_rendered_html = build_rendered_html.delay
