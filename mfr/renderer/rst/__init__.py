from .. import FileRenderer
from docutils.core import publish_parts
import os.path


class RstRenderer(FileRenderer):

    # Gets here using the .rst extension check then attempts to read the file
        # using docutils. If it can it accepts it as a valid file

    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        return ext.lower() == ".rst"

    def _render(self, file_pointer, url=None, **kwargs):
        return publish_parts(file_pointer.read(), writer_name='html')['html_body']