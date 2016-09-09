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
    return unicode(bib[0] if len(bib) else '')
