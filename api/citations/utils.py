import os
import re

from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc import formatter
from citeproc.source.json import CiteProcJSON

from website.preprints.model import PreprintService
from website.project.model import Node
from website.settings import CITATION_STYLES_PATH


def clean_up_common_errors(cit):
    cit = re.sub(r"\.+", '.', cit)
    cit = re.sub(r" +", ' ', cit)
    return cit


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

    cit = unicode(bib[0] if len(bib) else '')

    title = node.csl['title']
    if cit.count(title) == 1:
        i = cit.index(title)
        prefix = clean_up_common_errors(cit[0:i])
        suffix = clean_up_common_errors(cit[i + len(title):])
        cit = prefix + title + suffix
    elif cit.count(title) == 0:
        cit = clean_up_common_errors(cit)

    return cit
