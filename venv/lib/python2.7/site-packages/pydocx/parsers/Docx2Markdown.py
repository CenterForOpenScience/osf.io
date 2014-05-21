from pydocx.DocxParser import DocxParser


class Docx2Markdown(DocxParser):
    def escape(self, text):
        return text

    def linebreak(self):
        return '\n'

    def paragraph(self, text):
        return text + '\n'

    def insertion(self, text, author, date):
        pass

    def bold(self, text):
        return '**' + text + '**'

    def italics(self, text):
        # TODO do we need a "pre" variable, so I can check for
        # *italics**italics* and turn it into *italicsitatlics*?
        return '*' + text + '*'

    def underline(self, text):
        return '***' + text + '***'
