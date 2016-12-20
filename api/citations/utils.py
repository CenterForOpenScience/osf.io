import os
import re

from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc import formatter
from citeproc.source.json import CiteProcJSON

from website.preprints.model import PreprintService
from website.project.model import Node
from website.settings import CITATION_STYLES_PATH


def display_absolute_url(node):
    url = node.absolute_url
    if url is not None:
        return re.sub(r'https?:', '', url).strip('/')


def preprint_csl(preprint, node):
    csl = node.csl

    csl['id'] = preprint._id
    csl['publisher'] = preprint.provider.name
    csl['URL'] = display_absolute_url(preprint)

    if csl.get('DOI'):
        csl.pop('DOI')

    doi = preprint.article_doi
    if doi:
        csl['DOI'] = doi

    return csl


def render_citation(node, style='apa'):
    """Given a node, return a citation"""
    if isinstance(node, Node):
        data = [node.csl, ]
    elif isinstance(node, PreprintService):
        csl = preprint_csl(node, node.node)
        data = [csl, ]
    else:
        raise ValueError

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
        doi = data[0].get('DOI')
        if style == 'apa':
            first_segment = [list(bib[0])[0][:-2]]
            return ''.join(first_segment + list(bib[0])[1:13]) if doi else ''.join(first_segment + list(bib[0])[1:12] + list(bib[0])[13:])
        elif style == 'modern-language-association':
            return ''.join(list(bib[0])[:4] + ['.'] + list(bib[0])[4:5] + list(bib[0])[6:-2])
        elif style == 'chicago-author-date':
            return ''.join(list(bib[0])[0:3] + ['.'] + list(bib[0])[3:4] + [' '] + list(bib[0])[5:])
        else:
            return unicode(bib[0])
    else:
        return ''
