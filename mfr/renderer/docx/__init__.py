from .. import FileRenderer
import os.path
import pydocx


class DocxRenderer(FileRenderer):

    def is_openxml(self, file_pointer):
        """OpenXML Formats have a trailer with "PK," followed by 18 bytes.
        Returns true for docx, pptx, xlsx
        """
        docx_sig = 'PK'
        file_pointer.seek(-26, 2)
        tail = file_pointer.read()
        return docx_sig in tail

    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        if ext.lower() == '.docx':
            return self.is_openxml(file_pointer)
        return False

    def _render(self, file_pointer, **kwargs):
        # Use `_parsed` rather than `parsed` to avoid wrapping output in
        # html, body tags
        return pydocx.Docx2Html(file_pointer)._parsed
