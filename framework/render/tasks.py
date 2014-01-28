import logging
import os
from framework.tasks import celery
import time
from website import settings  # TODO: Use framework's config module instead
from mfr.renderer import FileRenderer
import mfr


logger = logging.getLogger(__name__)


config = {}
FileRenderer.STATIC_PATH = '/static/mfr'


@celery.task(time_limit=30000)
def build_rendered_html(file_path, cached_file_path, download_path):
    """

    Takes absolute and relative path to a file and builds the html used to render the file.
    Each render occurs is queued in celery.
    Writes the html to a file located at cached_file_path.
    :param file_pointer: relative path
    :param cached_file_path: route to cache location
    :param download_path: absolute path
    :return: html file in cached_file_path used to render file at the file_path

    """
    file_pointer = open(file_path)
    rendered = mfr.render(file_pointer, url=download_path)
    if rendered is None:
        rendered = 'Unable to render, download file to view it'.format(download_path)
    with open(cached_file_path, 'w') as fp:
        fp.write(rendered)
    return True