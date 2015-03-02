# -*- coding: utf-8 -*-

from flask import request

from modularodm import Q
from website.models import CitationStyle
from website.project.decorators import must_be_contributor_or_public


def list_citation_styles():
    query = None

    term = request.args.get('q')
    if term:
        query = (
            Q('_id', 'icontains', term) |
            Q('title', 'icontains', term) |
            Q('short_title', 'icontains', term)
        )

    return {
        'styles': [style.to_json() for style in CitationStyle.find(query)],
    }


@must_be_contributor_or_public
def node_citation(**kwargs):
    node = kwargs['node'] or kwargs['project']
    return {node.csl['id']: node.csl}
