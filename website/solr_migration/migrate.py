import re

from markdown import markdown
from modularodm.query.querydialect import DefaultQueryDialect as Q
from BeautifulSoup import BeautifulSoup

from framework import app
from website.models import Node, NodeWikiPage
from website.project.solr import (
    solr, migrate_solr, migrate_user, migrate_solr_wiki
)

ctx = app.test_request_context()
ctx.push()


def migrate_projects():
    # Projects
    # our first step is to delete all projects
    solr.delete_all()
    # and then commit that delete
    solr.commit()
    # find all public projects that are not deleted,
    # are public

    public_projects = Node.find(
        Q('category', 'eq', 'project') &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    )

    for project in public_projects:
        contributors = []
        contributors_url = []
        # get all of our users and the urls to their profile pages
        for user in project.contributors:
            if user is not None:
                # puts users in solr
                migrate_user({
                    'id': user._id,
                    'user': user.fullname,
                    'public': True,
                })
                contributors.append(user.fullname)
                contributors_url.append('/profile/{}'.format(user._id))
        id = project._id

        document = {
            'id': id,
            project._id + '_title': project.title,
            project._id + '_category': project.category,
            project._id + '_public': True,
            project._id + '_tags': [x._id for x in project.tags],
            project._id + '_description': project.description,
            project._id + '_url': project.url(),
            project._id + '_contributors': contributors,
            project._id + '_contributors_url': contributors_url,
            'public': True,
        }
        # send the document over
        migrate_solr(document)


def migrate_nodes():
    # now we find all public nodes that are not deleted
    # and do the same we did for projects
    public_nodes = Node.find(
        Q('category', 'ne', 'project') &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    )
    for node in public_nodes:
        contributors = []
        contributors_url = []
        for user in node.contributors:
            if user is not None:
                # put user in solr
                contributors.append(user.fullname)
                contributors_url.append('/profile/{}'.format(user._id))
        id = node.node__parent[0]._id
        document = {
            'id': id,
            node._id + '_title': node.title,
            node._id + '_category': node.category,
            node._id + '_public': True,
            node._id + '_tags': [x._id for x in node.tags],
            node._id + '_description': node.description,
            node._id + '_url': '/project/{}/node/{}/'.format(id, node._id),
            node._id + '_contributors': contributors,
            node._id + '_contributors_url': contributors_url,
        }
        # only migrate if the parent project is public, not deleted
        if node.node__parent[0].is_public:
            migrate_solr(document)


def migrate_wikis():
        # find all of our current wiki pages
        for wiki in NodeWikiPage.find(Q('is_current', 'eq', True)):

            if isinstance(wiki, NodeWikiPage):
                wiki = [wiki, ]

            for wik in wiki:
                wiki_content = wik.content
                remove_re = re.compile(
                    u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
                wiki_content = remove_re.sub('', wiki_content)
                html = markdown(wiki_content)
                wiki_content = ''.join(
                    BeautifulSoup(html).findAll(text=True))
                id = find_project_id(wik.node)
                if not id:
                    continue
                node_id = wik.node._id
                if not wik.node:
                    continue
                pagename = wik.page_name
                document = {
                    'id': id,
                    '__'.join((node_id, pagename, 'wiki')): wiki_content
                }
                migrate_solr_wiki(document)


def find_project_id(node):
    # find the project id
    try:
        if node.category == 'project':
            return node._id
        else:
            return node.node__parent[0]._id
    except IndexError:
        print('ERROR: Node {} is an orphan!'.format(node._id))


migrate_projects()
migrate_nodes()
migrate_wikis()

ctx.pop()