import base64
import xml.sax.saxutils

from pydocx.DocxParser import DocxParser


class Docx2Html(DocxParser):

    @property
    def parsed(self):
        content = self._parsed
        content = "<html>%(head)s<body>%(content)s</body></html>" % {
            'head': self.head(),
            'content': content,
        }
        return unicode(content)

    def head(self):
        return "<head>%(style)s</head>" % {
            'style': self.style(),
        }

    def style(self):
        result = (
            '<style>'
            '.pydocx-insert {color:green;}'
            '.pydocx-delete {color:red;text-decoration:line-through;}'
            '.pydocx-center {text-align:center;}'
            '.pydocx-right {text-align:right;}'
            '.pydocx-left {text-align:left;}'
            '.pydocx-comment {color:blue;}'
            '.pydocx-underline {text-decoration: underline;}'
            '.pydocx-caps {text-transform:uppercase;}'
            '.pydocx-small-caps {font-variant: small-caps;}'
            '.pydocx-strike {text-decoration: line-through;}'
            '.pydocx-hidden {visibility: hidden;}'
            'body {width:%(width)spx;margin:0px auto;}'
            '</style>'
        ) % {
            #multiple by (4/3) to get to px
            'width': (self.page_width * (4 / 3)),
        }
        return result

    def escape(self, text):
        return xml.sax.saxutils.quoteattr(text)[1:-1]

    def linebreak(self, pre=None):
        return '<br />'

    def paragraph(self, text, pre=None):
        return '<p>' + text + '</p>'

    def heading(self, text, heading_value):
        return '<%(tag)s>%(text)s</%(tag)s>' % {
            'tag': heading_value,
            'text': text,
        }

    def insertion(self, text, author, date):
        return (
            "<span class='pydocx-insert'>%(text)s</span>"
        ) % {
            'author': author,
            'date': date,
            'text': text,
        }

    def hyperlink(self, text, href):
        if text == '':
            return ''
        return '<a href="%(href)s">%(text)s</a>' % {
            'href': href,
            'text': text,
        }

    def image_handler(self, image_data, filename):
        extension = filename.split('.')[-1].lower()
        b64_encoded_src = 'data:image/%s;base64,%s' % (
            extension,
            base64.b64encode(image_data),
        )
        b64_encoded_src = self.escape(b64_encoded_src)
        return b64_encoded_src

    def image(self, image_data, filename, x, y):
        src = self.image_handler(image_data, filename)
        if not src:
            return ''
        if all([x, y]):
            return '<img src="%s" height="%s" width="%s" />' % (
                src,
                y,
                x,
            )
        else:
            return '<img src="%s" />' % src

    def deletion(self, text, author, date):
        return (
            "<span class='pydocx-delete'>%(text)s</span>"
        ) % {
            'author': author,
            'date': date,
            'text': text,
        }

    def list_element(self, text):
        return "<li>%(text)s</li>" % {
            'text': text,
        }

    def ordered_list(self, text, list_style):
        return '<ol list-style-type="%(list_style)s">%(text)s</ol>' % {
            'text': text,
            'list_style': list_style,
        }

    def unordered_list(self, text):
        return "<ul>%(text)s</ul>" % {
            'text': text,
        }

    def bold(self, text):
        return '<strong>' + text + '</strong>'

    def italics(self, text):
        return '<em>' + text + '</em>'

    def underline(self, text):
        return '<span class="pydocx-underline">' + text + '</span>'

    def caps(self, text):
        return '<span class="pydocx-caps">' + text + '</span>'

    def small_caps(self, text):
        return '<span class="pydocx-small-caps">' + text + '</span>'

    def strike(self, text):
        return '<span class="pydocx-strike">' + text + '</span>'

    def hide(self, text):
        return '<span class="pydocx-hidden">' + text + '</span>'

    def superscript(self, text):
        return '<sup>%(text)s</sup>' % {
            'text': text,
        }

    def subscript(self, text):
        return '<sub>%(text)s</sub>' % {
            'text': text,
        }

    def tab(self):
        # Insert before the text right?? So got the text and just do an insert
        # at the beginning!
        return '&nbsp&nbsp&nbsp&nbsp'

    def table(self, text):
        return '<table border="1">' + text + '</table>'

    def table_row(self, text):
        return '<tr>' + text + '</tr>'

    def table_cell(self, text, col='', row=''):
        slug = '<td'
        if col:
            slug += ' colspan="%(colspan)s"'
        if row:
            slug += ' rowspan="%(rowspan)s"'
        slug += '>%(text)s</td>'
        return slug % {
            'colspan': col,
            'rowspan': row,
            'text': text,
        }

    def page_break(self):
        return '<hr />'

    def indent(self, text, just='', firstLine='', left='', right=''):
        slug = '<div'
        if just:
            slug += " class='pydocx-%(just)s'"
        if firstLine or left or right:
            slug += " style='"
            if firstLine:
                slug += "text-indent:%(firstLine)spx;"
            if left:
                slug += "margin-left:%(left)spx;"
            if right:
                slug += "margin-right:%(right)spx;"
            slug += "'"
        slug += ">%(text)s</div>"
        return slug % {
            'text': text,
            'just': just,
            'firstLine': firstLine,
            'left': left,
            'right': right,
        }

    def break_tag(self):
        return '<br />'
