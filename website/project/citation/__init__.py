import os

from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import Citation, CitationItem
from citeproc import formatter
from citeproc.source.json import CiteProcJSON

from website.settings import CITATION_STYLES_PATH


def render(node, style='apa'):
    """Given a node, return a citation"""
    data = _node_to_csl_json(node)

    bib_source = CiteProcJSON(data)

    bib_style = CitationStylesStyle(os.path.join(CITATION_STYLES_PATH, style), validate=False)

    bibliography = CitationStylesBibliography(bib_style, bib_source, formatter.plain)

    citation = Citation([CitationItem(node._id)])

    bibliography.register(citation)

    def warn(citation_item):
        pass

    bibliography.cite(citation, warn)
    return unicode(bibliography.bibliography()[0])



def _node_to_csl_json(node):
    """Given a node, return a dict in CSL-JSON schema

    For details on this schema, see:
        https://github.com/citation-style-language/schema#csl-json-schema
    """
    return [{
        'author': [
            _user_to_csl_json(user) for user in node.visible_contributors
        ],
        'id': str(node._id),
        'issued': _datetime_to_csl_json(node.date_modified),
        'publisher': 'Open Science Framework',
        'title': unicode(node.title),
        # TODO: Use appropriate type for components (e.g.: "dataset")
        'type': 'article',
        'URL': node.absolute_url,
    }]


def _user_to_csl_json(user):
    """Given a user, return a dict in CSL-JSON name-variable schema"""
    return {
        'given': user.given_name,
        'family': user.family_name,
    }


def _datetime_to_csl_json(dt):
    """Given a datetime, return a dict in CSL-JSON date-variable schema"""
    return {'date-parts': [[dt.year, dt.month, dt.day]]}