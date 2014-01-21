import logging
import os
from framework.tasks import celery
import time
from website import settings  # TODO: Use framework's config module instead
from mfr.renderer import FileRenderer
from mfr.renderer import tabular, pdf, code, ipynb, image
logger = logging.getLogger(__name__)


config = {
    'ImageRenderer': {'max_width': '400px'},
}
FileRenderer.STATIC_PATH = '/static/mfr'


@celery.task(time_limit=30000)
def build_rendered_html(file_path, cached_file_path, download_path):
    """

    Takes absolute and relative path to a file and builds the html used to render the file.
    Each render occurs is queued in celery.
    Writes the html to a file located at cached_file_path.
    :param file_path: relative path
    :param cached_file_path: route to cache location
    :param download_path: absolute path
    :return: html file in cached_file_path used to render file at the file_path

    """

    FileRenderer.STATIC_PATH = '/static/mfr'
    file_pointer = open(file_path)
    for name, cls in FileRenderer.registry.items():
        renderer = cls(**config.get(name, {}))
        if renderer.detect(file_pointer):
            rendered = renderer._render(
                file_pointer, file_path, url=download_path
            )
    if not rendered:
        rendered = 'This file type cannot currently be rendered, please <a href={}>download</a> the file to view it'.format(download_path)
    with open(cached_file_path, 'w') as fp:
        fp.write(rendered)
    return True
