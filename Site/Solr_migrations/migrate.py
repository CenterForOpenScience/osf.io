from framework.Auth import User
from Site.Project import Node
from Site.Project import NodeWikiPage
from Site.Project.Solr import solr, \
    migrate_solr, migrate_user, migrate_solr_wiki
import re
from BeautifulSoup import BeautifulSoup
from markdown import markdown


def migrate_projects():
    # Projects
    # our first step is to delete all projects
    solr.delete_all()
    # and then commit that delete
    solr.commit()
    # find all public projects that are not deleted,
    # are public
    public_projects = Node.find(
        category='project',
        is_public=True,
        is_deleted=False,
    )

    for project in public_projects:
        contributors = []
        contributors_url = []
        # get all of our users and the urls to their profile pages
        for contributor in project['contributors']:
            user = User.find(_id=contributor)
            if user is not None:
                # puts users in solr
                migrate_user({
                    'id': contributor,
                    'user': user['fullname'],
                    'public': True,
                })
                contributors.append(user['fullname'])
                contributors_url.append('/profile/'+contributor)
        id = project['_id']
        # call our get url function
        url = get_url(project)
        document = {
            'id': id,
            project['_id']+'_title': project['title'],
            project['_id']+'_category': project['category'],
            project['_id']+'_public': True,
            project['_id']+'_tags': project['tags'],
            project['_id']+'_description': project['description'],
            project['_id']+'_url': url,
            project['_id']+'_contributors': contributors,
            project['_id']+'_contributors_url': contributors_url,
            'public': True,
        }
        # send the document over
        migrate_solr(document)


def migrate_nodes():
    # now we find all public nodes that are not deleted
    # and do the same we did for projects
    public_nodes = Node.find(
        category={'$ne': 'project'},
        is_public=True,
        is_deleted=False,
    )
    for node in public_nodes:
        contributors = []
        contributors_url = []
        for contributor in node['contributors']:
            user = User.find(_id=contributor)
            user['_id']
            if user is not None:
                # put user in solr
                contributors.append(user['fullname'])
                contributors_url.append('/profile/'+contributor)
        id = node['_b_node_parent']
        document = {
            'id': id,
            node['_id']+'_title': node['title'],
            node['_id']+'_category': node['category'],
            node['_id']+'_public': True,
            node['_id']+'_tags': node['tags'],
            node['_id']+'_description': node['description'],
            node['_id']+'_url': '/project/'+id+'/node/'+node['_id'],
            node['_id']+'_contributors': contributors,
            node['_id']+'_contributors_url': contributors_url,
        }
        # only migrate if the parent project is public, not deleted
        if Node.find(_id=id, is_public=True, is_deleted=False) is not None:
            migrate_solr(document)


def migrate_wikis():
        # find all of our current wiki pages
        wikis = NodeWikiPage.find(is_current=True)
        for wiki in wikis:
            # some wikis return cursors, some dont. check for that
            if not str(type(wiki)) == "<class 'pymongo.cursor.Cursor'>":
                # if its not a cursor, we just go ahead and get the content
                wiki_content = wiki['content']
                # now we strip out all the special markdown syntax
                remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
                wiki_content = remove_re.sub('', wiki_content)
                html = markdown(wiki_content)
                wiki_content = ''.join(BeautifulSoup(html).findAll(text=True))
                # find the project id that is public, not deleted
                id = find_project_id(wiki['node'])
                # if we dont get an id, continue
                if not id:
                    continue
                # get the id of the node
                node_id = wiki['node']
                # get the node that is public, and is not deleted
                node = Node.find(_id=node_id, is_public=True, is_deleted=False)
                # if we dont get a node, continue
                if not node:
                    continue
                pagename = wiki['page_name']
                document = {
                    'id': id,
                    node_id+'__'+pagename+'__wiki': wiki_content
                }
                migrate_solr_wiki(document)
            else:
                # if we get a cursor
                # (i.e., multiple wiki pages, we iterate through those)
                for wik in wiki:
                    wiki_content = wik['content']
                    remove_re = re.compile(
                        u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
                    wiki_content = remove_re.sub('', wiki_content)
                    html = markdown(wiki_content)
                    wiki_content = ''.join(
                        BeautifulSoup(html).findAll(text=True))
                    id = find_project_id(wiki['node'])
                    if not id:
                        continue
                    node_id = wiki['node']
                    node = Node.find(
                        _id=node_id, is_public=True, is_deleted=False)
                    if not node:
                        continue
                    pagename = wiki['page_name']
                    document = {
                        'id': id,
                        node_id+'__'+pagename+'__wiki': wiki_content
                    }
                    migrate_solr_wiki(document)


def find_project_id(id):
    # find the project id
    node = Node.find(_id=id, is_public=True, is_deleted=False)
    if node is None:
        return ''
    if node['category'] == 'project':
        return id
    else:
        return node['_b_node_parent']


def get_url(node):
    # builds the url
    if node['category'] == 'project':
        return '/project/' + node['_id']
    else:
        return '/project/' + node['_b_node_parent'] + '/node/' + node['_id']


migrate_projects()
migrate_nodes()
migrate_wikis()
