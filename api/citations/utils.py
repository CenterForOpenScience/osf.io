import os

from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc import formatter
from citeproc.source.json import CiteProcJSON

from website.settings import CITATION_STYLES_PATH


def render_citation(node, style='apa'):
    """Given a node, return a citation"""
    data = [node.csl, ]

    bib_source = CiteProcJSON(data)

    bib_style = CitationStylesStyle(os.path.join(CITATION_STYLES_PATH, style), validate=False)

    bibliography = CitationStylesBibliography(bib_style, bib_source, formatter.plain)

    citation = Citation([CitationItem(node._id)])

    bibliography.register(citation)

    def warn(citation_item):
        pass

    bibliography.cite(citation, warn)
    bib = bibliography.bibliography()

    if len(bib):
        if style == 'apa':
            return ''.join([list(bib[0])[0][:-2]] + list(bib[0])[1:12] + list(bib[0])[13:])
        elif style == 'modern-language-association':
            return ''.join(list(bib[0])[:4] + ['.'] + list(bib[0])[4:5] + list(bib[0])[6:-2])
        elif style == 'chicago-author-date':
            return ''.join(list(bib[0])[0:3] + ['.'] + list(bib[0])[3:4] + [' '] + list(bib[0])[5:])
        else:
            return unicode(bib[0])
    else:
        return ''
