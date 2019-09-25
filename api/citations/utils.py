import os
import re
from rest_framework import status as http_status

from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc import formatter
from citeproc.source.json import CiteProcJSON

from framework.exceptions import HTTPError
from framework.auth import utils
from osf.models.citation import CitationStyle
from website.settings import CITATION_STYLES_PATH, BASE_PATH, CUSTOM_CITATIONS


def clean_up_common_errors(cit):
    cit = re.sub(r'\.+', '.', cit)
    cit = re.sub(r' +', ' ', cit)
    return cit

def process_name(node, user):
    # If the user has a family and given name, use those
    if user.family_name and user.given_name:
        return {
            'family_name': user.family_name,
            'suffix': user.suffix,
            'given_name': user.given_name,
            'middle_names': user.middle_names,
        }
    elif user.is_registered or user.is_disabled:
        name = user.fullname
    else:
        name = user.get_unclaimed_record(node._id)['name']

    # If the user doesn't autofill his family and given name
    parsed = utils.impute_names(name)
    return {
        'family_name': parsed['family'],
        'suffix': parsed['suffix'],
        'given_name': parsed['given'],
        'middle_names': parsed['middle'],
    }


def render_citation(node, style='apa'):
    """Given a node, return a citation"""
    reformat_styles = ['apa', 'chicago-author-date', 'modern-language-association']
    csl = node.csl
    data = [csl, ]

    bib_source = CiteProcJSON(data)

    custom = CUSTOM_CITATIONS.get(style, False)
    path = os.path.join(BASE_PATH, 'static', custom) if custom else os.path.join(CITATION_STYLES_PATH, style)

    try:
        bib_style = CitationStylesStyle(path, validate=False)
    except ValueError:
        citation_style = CitationStyle.load(style)
        if citation_style is not None and citation_style.has_parent_style:
            parent_style = citation_style.parent_style
            parent_path = os.path.join(CITATION_STYLES_PATH, parent_style)
            bib_style = CitationStylesStyle(parent_path, validate=False)
        else:
            raise ValueError('Unable to find a dependent or independent parent style related to {}.csl'.format(style))

    bibliography = CitationStylesBibliography(bib_style, bib_source, formatter.plain)

    citation = Citation([CitationItem(node._id)])

    bibliography.register(citation)

    bib = bibliography.bibliography()
    cit = unicode(bib[0] if len(bib) else '')

    title = csl['title'] if csl else node.csl['title']
    title = title.rstrip('.')
    if cit.count(title) == 1:
        i = cit.index(title)
        prefix = clean_up_common_errors(cit[0:i])
        suffix = clean_up_common_errors(cit[i + len(title):])
        if (style in reformat_styles):
            if suffix[0:1] == '.':
                suffix = suffix[1:]
            if title[-1] != '.':
                title += '.'
        cit = prefix + title + suffix
    elif cit.count(title) == 0:
        cit = clean_up_common_errors(cit)
        if (style in reformat_styles):
            cit = add_period_to_title(cit)

    if style == 'apa':
        cit = apa_reformat(node, cit)
    if style == 'chicago-author-date':
        cit = chicago_reformat(node, cit)
    if style == 'modern-language-association':
        cit = mla_reformat(node, cit)

    return cit

def add_period_to_title(cit):
    title_split = cit.encode('utf-8').split('\xe2\x80\x9d')
    if len(title_split) == 2 and title_split[0][-1] != '.':
        cit = (title_split[0] + '.' + '\xe2\x80\x9d' + title_split[1]).decode('utf-8')
    return cit

def apa_reformat(node, cit):
    new_csl = cit.split('(')
    contributors_list = list(node.visible_contributors)
    contributors_list_length = len(contributors_list)

    # throw error if there is no visible contributor
    if contributors_list_length == 0:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    # handle only one contributor
    elif contributors_list_length == 1:
        name = process_name(node, contributors_list[0])
        new_apa = apa_name(name)
    # handle more than one contributor but less than 8 contributors
    elif contributors_list_length in range(1, 8):
        name_list = [apa_name(process_name(node, x)) for x in contributors_list[:-1]]
        new_apa = ' '.join(name_list)
        last_one = apa_name(process_name(node, contributors_list[-1]))
        new_apa += ' & ' + last_one
    # handle 8 or more contributors
    else:
        name_list = [apa_name(process_name(node, x)) for x in contributors_list[:6]]
        new_apa = ' '.join(name_list) + ' \xe2\x80\xa6 '.decode('utf-8') + apa_name(process_name(node, contributors_list[-1]))

    cit = new_apa.rstrip(', ')
    if cit[-1] != '.':
        cit += '.'
    for x in new_csl[1:]:
        cit += ' (' + x
    return cit


def apa_name(name):
    apa = ''
    if name['family_name']:
        apa += name['family_name'] + ','
    if name['given_name']:
        apa += ' ' + name['given_name'][0] + '.'
        if name['middle_names']:
            apa += middle_name_splitter(name['middle_names'])
        apa += ','
    if name['suffix']:
        apa += ' ' + name['suffix'] + ','
    return apa


def mla_reformat(node, cit):
    contributors_list = list(node.visible_contributors)
    contributors_list_length = len(contributors_list)
    cit = remove_extra_period_after_right_quotation(cit)
    cit_minus_authors = ('\xe2\x80\x9c' + cit.encode('utf-8').split('\xe2\x80\x9c')[1]).decode('utf-8')

    # throw error if there is no visible contributor
    if contributors_list_length == 0:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    # handle only one contributor
    elif contributors_list_length == 1:
        name = process_name(node, contributors_list[0])
        new_mla = mla_name(name, initial=True).rstrip(', ')
    # handle more than one contributor but less than 5 contributors
    elif contributors_list_length == 2:
        first_one = mla_name(process_name(node, contributors_list[0]), initial=True)
        last_one = mla_name(process_name(node, contributors_list[-1]))
        new_mla = first_one.rstrip(',') + ', and ' + last_one
    else:
        name = process_name(node, contributors_list[0])
        new_mla = mla_name(name, initial=True).rstrip(', ') + ', et al.'

    if new_mla[-1] != '.':
        new_mla = new_mla + '.'
    return new_mla + ' ' + cit_minus_authors

def remove_extra_period_after_right_quotation(cit):
    return cit.encode('utf-8').replace('\xe2\x80\x9d.', '\xe2\x80\x9d').decode('utf-8')

def chicago_reformat(node, cit):
    cit = remove_extra_period_after_right_quotation(cit)
    issued = node.csl.get('issued')
    new_csl = cit.split(str(issued['date-parts'][0][0]) if issued else 'n.d.', 1)
    contributors_list = list(node.visible_contributors)
    contributors_list_length = len(contributors_list)
    # throw error if there is no visible contributor
    if contributors_list_length == 0:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    # handle only one contributor
    elif contributors_list_length == 1:
        name = process_name(node, contributors_list[0])
        new_chi = mla_name(name, initial=True)
        new_chi = new_chi.rstrip(',')
    # handle more than one contributor but less than 8 contributors
    elif contributors_list_length in range(1, 8):
        first_one = mla_name(process_name(node, contributors_list[0]), initial=True).rstrip(',')
        rest_ones = [mla_name(process_name(node, x)) for x in contributors_list[1:-1]]
        last_one = mla_name(process_name(node, contributors_list[-1]))
        if rest_ones:
            rest_part = ', '.join(rest_ones)
            new_chi = first_one + ', ' + rest_part + ', and ' + last_one
        else:
            new_chi = first_one + ', and ' + last_one
    # handle 8 or more contributors
    else:
        new_chi = mla_name(process_name(node, contributors_list[0]), initial=True).rstrip(', ')
        name_list = [mla_name(process_name(node, x)) for x in contributors_list[1:7]]
        rest = ', '.join(name_list)
        rest = rest.rstrip(',') + ', et al.'
        new_chi += ', ' + rest
    if new_chi[-1] != '.':
        new_chi += '.'
    cit = new_chi
    for x in new_csl[1:]:
        year = str(issued['date-parts'][0][0]) if issued else 'n.d.'
        cit += ' ' + year + x
    return cit

def mla_name(name, initial=False):
    if initial:
        mla = ''
        if name['family_name']:
            mla += name['family_name'] + ','
        if name['given_name']:
            mla += ' ' + name['given_name']
            if name['middle_names']:
                mla += middle_name_splitter(name['middle_names'])
            mla += ','
        if name['suffix']:
            mla += ' ' + name['suffix']
    else:
        mla = ''
        if name['given_name']:
            mla += name['given_name']
            if name['middle_names']:
                mla += middle_name_splitter(name['middle_names'])
        if name['family_name']:
            mla += ' ' + name['family_name']
        if name['suffix']:
            mla += ', ' + name['suffix']
    return mla

def middle_name_splitter(middle_names):
    initials = ''
    if middle_names:
        middle_names = middle_names.strip()
    middle_names_arr = middle_names.split(' ')
    for name in middle_names_arr:
        initials += ' ' + name[0] + '.'
    return initials
