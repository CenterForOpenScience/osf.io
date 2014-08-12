import logging
import importlib
from .renderer.exceptions import NoRendererError
from mfr.renderer import FileRenderer

logger = logging.getLogger(__name__)

modules = [
    'image', 'pdf', 'pdb', 'code', 'ipynb', 'docx', 'audio',
    'tabular.renderers', 'rst',
]
for module in modules:
    try:
        importlib.import_module('mfr.renderer.' + module)
    except ImportError as err:
        logger.exception(err)
        logger.error('Could not import module {0}'.format(module))

config = {}


def detect(file_pointer):
    for name, cls in FileRenderer.registry.items():
        renderer = cls(**config.get(name, {}))
        if renderer._detect(file_pointer):
            return renderer
    return None


def render(file_pointer, *args, **kwargs):
    renderer = detect(file_pointer)
    if renderer is None:
        raise NoRendererError("No renderer currently available for this file type.")
    return renderer.render(file_pointer, *args, **kwargs)
