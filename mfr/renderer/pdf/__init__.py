from .. import FileRenderer
import PyPDF2
import os.path



class PdfRenderer(FileRenderer):

    # Gets here using the .pdf extension check then attempts to read the file
        # using pydf2, if it can it accepts it as a valid pdf

    def _detect(self, file_pointer):
        _, ext = os.path.splitext(file_pointer.name)
        if ext.lower() == ".pdf":
            try:
                PyPDF2.PdfFileReader(file_pointer)
            except PyPDF2.utils.PdfReadError:
                return False
            return True
        return False

    def _render(self, file_pointer, url=None, **kwargs):
        return self._render_mako(
            "pdfpage.mako",
            url=url,
            STATIC_PATH=self.STATIC_PATH,
        )
