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
from framework.auth import utils

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


def process_name(node, user):
    if user.is_registered or user.is_disabled:
        name = user.fullname
    else:
        name = user.get_unclaimed_record(node._id)['name']

    if user.family_name and user.given_name:
        """If the user has a family and given name, use those"""
        return {
            'family_name': user.family_name,
            'suffix': user.suffix,
            'given_name': user.csl_given_name,
            'middle_names': user.middle_names,
        }
    else:
        """ If the user doesn't autofill his family and given name """
        parsed = utils.impute_names(name)
        given_name = parsed['given']
        middle_names = parsed['middle']
        family_name = parsed['family']
        suffix = parsed['suffix']
        return {
            'family_name': family_name,
            'suffix': suffix,
            'given_name': given_name,
            'middle_names': middle_names
        }

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

    return cit


def apa_reformat(node, cit):
    new_csl = cit.split('(')[1]
    new_apa = ''
    contributors_list = [x for x in node.contributors if node.get_visible(x)]
    if len(contributors_list) == 1:
        name = process_name(node, contributors_list[0])
        new_apa = apa_name(name)
    else:
        name_list = [apa_name(process_name(node, x)) for x in contributors_list]
        if len(contributors_list) in range(1, 8):
            new_apa = '& '.join(name_list)
        if len(contributors_list) > 7:
            new_apa = ' '.join(name_list)
    cit = new_apa + '(' + new_csl
    return cit

def apa_name(name):
    apa_name = ''
    if name['family_name']:
        apa_name += name['family_name'] + ', '
    if name['given_name']:
        apa_name += name['given_name'][0] + '.'
        if name['middle_names']:
            apa_name += ' ' + name['middle_names'][0] + '.'
        apa_name += ', '
    if name['suffix']:
        apa_name += name['suffix'] + ' '
    return apa_name

def mla_reformat(node, cit):
    new_csl = cit.split('(')[1]
    new_apa = ''
    contributors_list = [x for x in node.contributors if node.get_visible(x)]
    if len(contributors_list) == 1:
        name = process_name(node, contributors_list[0])
        new_apa = mla_name(name)
    else:
        name_list = [apa_name(process_name(node, x)) for x in contributors_list]
        if len(contributors_list) in range(1, 5):
            new_apa = '& '.join(name_list)
        if len(contributors_list) > 4:
            new_apa = ' '.join(name_list)
    cit = new_apa + '(' + new_csl
    return cit

def chicago_reformat(node, cit):
    return cit


def mla_name(name, inital=False):
    if inital:
        mla_name = ''
        if name['family_name']:
            mla_name += name['family_name'] + ', '
        if name['given_name']:
            mla_name += name['given_name']
            if name['middle_names']:
                mla_name += ' ' + name['middle_names'][0] + '.'
            mla_name += ', '
        if name['suffix']:
            mla_name += name['suffix'] + ' '
    else:
        mla_name = ''
        if name['given_name']:
            mla_name += name['given_name']
            if name['middle_names']:
                mla_name += ' ' + name['middle_names'][0]
            mla_name += ', '
        if name['suffix']:
            mla_name += name['suffix'] + ' '
            