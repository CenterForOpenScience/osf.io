import os

from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc import formatter
from citeproc.source.json import CiteProcJSON

from website.settings import CITATION_STYLES_PATH


def render(node, style='apa'):
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
    return unicode(bibliography.bibliography()[0])


def render_iterable(data, style='apa'):
    """Render an iterable of CSL-data to an iterable of text"""
    data = list(data)

    bib_source = CiteProcJSON(data)

    bib_style = CitationStylesStyle(os.path.join(CITATION_STYLES_PATH, style), validate=False)

    bibliography = CitationStylesBibliography(bib_style, bib_source, formatter.plain)

    citations = [
        Citation([CitationItem(each['id'])])
        for each in data
    ]

    for citation in citations:
        bibliography.register(citation)

    def warn(citation_item):
        pass

    for citation in citations:
        bibliography.cite(citation, warn)

    return (unicode(citation) for citation in bibliography.bibliography())
