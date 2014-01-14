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


# def render(file_name, **kwargs):
#     file_pointer = open(file_name)
#     for name, cls in FileRenderer.registry.items():
#         renderer = cls(**config.get(name, {}))
#         if renderer.detect(file_pointer):
#             return renderer._render(file_pointer, file_name, **kwargs)
#     return file_name
#
#
# @celery.task
# def build_rendered_html(file_path, cached_file_path, download_path):
#     rendered = render(file_path, url=download_path)
#     with open(cached_file_path, 'w') as fp:
#         fp.write(rendered)
#     return True


@celery.task
def build_rendered_html(file_path, cached_file_path, download_path):
    FileRenderer.STATIC_PATH = '/static/mfr'
    file_pointer = open(file_path)
    for name, cls in FileRenderer.registry.items():
        renderer = cls(**config.get(name, {}))
        if renderer.detect(file_pointer):
            rendered = renderer._render(
                file_pointer, file_path, url=download_path
            )
    with open(cached_file_path, 'w') as fp:
        fp.write(rendered)
    return True
