from .. import FileRenderer
import re
import os.path
from IPython.config import Config
# from IPython.nbconvert import export_python
from IPython.nbconvert.exporters import HTMLExporter
from IPython.nbformat import current as nbformat

c = Config()
c.HTMLExporter.template_file = 'basic'
c.NbconvertApp.fileext = 'html'
c.CSSHTMLHeaderTransformer.enabled = False
c.Exporter.filters = {'strip_files_prefix': lambda s: s} #don't strip the files prefix
exporter = HTMLExporter(config=c)


class NbFormatError(Exception):
    pass


class IPynbRenderer(FileRenderer):
    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        return ext.lower() == '.ipynb'

    def _render(self, file_pointer, **kwargs):
        content = file_pointer.read()
        nb = self._parse_json(content)
        name, theme = self._get_metadata(nb)
        body = exporter.from_notebook_node(nb)[0]
        return self._render_mako(
            "ipynb.mako", file_name=name, css_theme=theme, mathjax_conf=None,
            body=body, STATIC_PATH=self.STATIC_PATH
        )

    def _parse_json(self, content):
        try:
            nb = nbformat.reads_json(content)
        except ValueError:
            raise NbFormatError('Error reading json notebook')
        return nb

    def _get_metadata(self, nb):
        # notebook title
        name = nb.get('metadata', {}).get('name', None)
        if not name:
            name = "untitled.ipynb"
        if not name.endswith(".ipynb"):
            name += ".ipynb"

        # css
        css_theme = nb.get('metadata', {})\
                      .get('_nbviewer', {})\
                      .get('css', None)
        if css_theme and not re.match('\w', css_theme):
            css_theme = None
        return name, css_theme