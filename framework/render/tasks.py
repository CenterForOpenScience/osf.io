import logging
import os
import errno
from framework.tasks import celery
from website import settings  # TODO: Use framework's config module instead
from mfr.renderer import FileRenderer
import mfr
import tempfile

logger = logging.getLogger(__name__)


config = {}
FileRenderer.STATIC_PATH = '/static/mfr'


def ensure_path(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


@celery.task(time_limit=settings.MFR_TIMEOUT)
def _build_rendered_html(file_name, file_content, cache_dir, cache_file_name, download_path):
    """

    :param str file_name:
    :param str file_content:
    :param str cache_dir:
    :param str cache_file_name:
    :param str download_path:

    """
    # Open or create file pointer
    if file_content is None:
        file_pointer = open(file_name)
    else:
        file_pointer = tempfile.NamedTemporaryFile(
            suffix=os.path.splitext(file_name)[1],
        )
        file_pointer.write(file_content)
        file_pointer.seek(0)

    # Build path to cached content
    ensure_path(cache_dir)
    cache_file_path = os.path.join(cache_dir, cache_file_name)

    # Render file
    rendered = mfr.render(file_pointer, url=download_path)
    if rendered is None:
        rendered = 'Unable to render; download file to view it'.format(download_path)

    # Close read pointer
    file_pointer.close()

    # Cache rendered content
    with open(cache_file_path, 'w') as write_file_pointer:
        write_file_pointer.write(rendered)

    return True

# Expose render function
build_rendered_html = _build_rendered_html
if settings.MFR_USE_QUEUE:
    build_rendered_html = build_rendered_html.delay
