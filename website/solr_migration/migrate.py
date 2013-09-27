import re

from markdown import markdown
from modularodm.query.querydialect import DefaultQueryDialect as Q
from BeautifulSoup import BeautifulSoup

from framework import app
from website.models import Node, NodeWikiPage
from website.project.solr import (
    solr, migrate_solr_wiki
)

ctx = app.test_request_context()
ctx.push()


def migrate_nodes():
    # Projects
    # our first step is to delete all projects
    solr.delete_all()
    # and then commit that delete
    solr.commit()
    # find all public projects that are not deleted,
    # are public

    for node in Node.find(
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    ):
        node.update_solr()


def find_project_id(node):
    # find the project id
    try:
        if node.category == 'project':
            return node._id
        else:
            return node.node__parent[0]._id
    except IndexError:
        print('ERROR: Node {} is an orphan!'.format(node._id))


migrate_nodes()

ctx.pop()