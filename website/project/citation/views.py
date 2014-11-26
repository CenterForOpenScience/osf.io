import httplib as http

from flask import request
from modularodm import Q

from framework.exceptions import HTTPError
from website.models import CitationStyle
from website.project import citation
from website.project.decorators import must_be_contributor_or_public


def styles():
    query = None

    term = request.args.get('q')
    if term:
        query = Q('title', 'icontains', term) | Q('short_title', 'icontains', term) | Q('_id', 'icontains', term)

    return {
        'styles': [style.to_json() for style in CitationStyle.find(query)],
    }


@must_be_contributor_or_public
def view_citation(**kwargs):
    node = kwargs.get('node') or kwargs.get('project')
    try:
        citation_text = citation.render(node, style=kwargs.get("style"))
    except ValueError:
        raise HTTPError(http.NOT_FOUND,
                        data={"message_short": "Invalid citation style"})

    return {
        'citation': citation_text,
    }