import os
import re
import logging

from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc import formatter
from citeproc.source.json import CiteProcJSON

from osf.models import PreprintService
from website.citations.utils import datetime_to_csl
from website.settings import CITATION_STYLES_PATH, BASE_PATH, CUSTOM_CITATIONS

logger =logger = logging.getLogger(__name__)


def clean_up_common_errors(cit):
    cit = re.sub(r"\.+", '.', cit)
    cit = re.sub(r" +", ' ', cit)
    return cit


def display_absolute_url(node):
    url = node.absolute_url
    if url is not None:
        return re.sub(r'https?:', '', url).strip('/')


def preprint_csl(preprint, node):
    csl = node.csl

    csl['id'] = preprint._id
    csl['publisher'] = preprint.provider.name
    csl['URL'] = display_absolute_url(preprint)

    if preprint.original_publication_date:
        csl['issued'] = datetime_to_csl(preprint.original_publication_date)

    if csl.get('DOI'):
        csl.pop('DOI')

    doi = preprint.article_doi
    if doi:
        csl['DOI'] = doi

    return csl


def render_citation(node, style='apa'):
    """Given a node, return a citation"""
    csl = None
    if isinstance(node, PreprintService):
        csl = preprint_csl(node, node.node)
        data = [csl, ]
    else:
        data = [node.csl, ]

    bib_source = CiteProcJSON(data)

    custom = CUSTOM_CITATIONS.get(style, False)
    path = os.path.join(BASE_PATH, 'static', custom) if custom else os.path.join(CITATION_STYLES_PATH, style)
    bib_style = CitationStylesStyle(path, validate=False)

    bibliography = CitationStylesBibliography(bib_style, bib_source, formatter.plain)

    citation = Citation([CitationItem(node._id)])

    bibliography.register(citation)

    bib = bibliography.bibliography()
    cit = unicode(bib[0] if len(bib) else '')

    title = csl['title'] if csl else node.csl['title']
    if cit.count(title) == 1:
        i = cit.index(title)
        prefix = clean_up_common_errors(cit[0:i])
        suffix = clean_up_common_errors(cit[i + len(title):])
        cit = prefix + title + suffix
    elif cit.count(title) == 0:
        cit = clean_up_common_errors(cit)

    if style == 'apa':
        cit = apa_reformat(node, cit)
    if style == 'chicago-author-date':
        cit = chicago_reformat(node, cit)
    if style == 'modern-language-association':
        cit = mla_reformat(node, cit)
    logger.info(node.contributors)
    logger.info(style)
    logger.info('--------------')
    logger.info('cit')
    logger.info(cit)
    logger.info('--------------')

    return cit


def apa_reformat(node, cit):
    new_csl = cit.split('(')[1]
    if len(node.contributors) == 1:
        process_apa_name(node.contributors[0])
    if len(node.contributors) >1 and len(node.contributors) < 8:
        new_csl_name_list = [process_apa_name(x) for x in node.contributors]


    return cit

def mla_reformat(node, cit):
    return cit

def chicago_reformat(node, cit):
    return cit


def process_apa_name(user):
    return user