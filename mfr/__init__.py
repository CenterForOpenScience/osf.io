from mfr.renderer import FileRenderer
#from mfr.renderer import image, tabular, pdf, code, ipynb

from mfr.renderer import image, pdf, code, ipynb


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
        return None
    return renderer.render(file_pointer, *args, **kwargs)