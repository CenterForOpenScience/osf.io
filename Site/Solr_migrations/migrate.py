from framework.Auth import User
from Site.Project import Node
from Site.Project import NodeWikiPage
from Site.Project.Solr import solr, migrate_solr
import re
from BeautifulSoup import BeautifulSoup
from markdown import markdown



def migrate_projects():
    # Projects
    solr.delete_all()
    solr.commit()
    public_projects = Node.find(
        category='project',
        is_public=True,
        is_deleted=False,
        is_registration=False
    )

    for project in public_projects:
        contributors = []
        contributors_url = []
        for contributor in project['contributors']:
            user = User.find(_id=contributor)
            if user is not None:
                contributors.append(user['fullname'])
                contributors_url.append('/profile/'+contributor)
        id = project['_id']
        url =  get_url(project)
        if NodeWikiPage.find(
                node=project['_id'], is_current=True, page_name='home') is not None and 'content' in NodeWikiPage.find(
                node=project['_id'], is_current=True):
            wiki = NodeWikiPage.find(
                node=project['_id'], is_current=True)['content']
            remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
            wiki = remove_re.sub('', wiki)
            html = markdown(wiki)
            wiki = ''.join(BeautifulSoup(html).findAll(text=True))
        else:
            wiki = None
        document = {
            'id': id,
            project['_id']+'_title': project['title'],
            project['_id']+'_category':project['category'],
            project['_id']+'_public':True,
            project['_id']+'_tags':project['tags'],
            project['_id']+'_description':project['description'],
            project['_id']+'_url':url,
            project['_id']+'_wiki':wiki,
            'contributors':contributors,
            'contributors_url': contributors_url,
        }
        print document
        migrate_solr(document)


def migrate_nodes():
    public_nodes = Node.find(
        category={'$ne':'project'},
        is_public=True,
        is_deleted=False,
        is_registration=False
    )
    for node in public_nodes:
        contributors = []
        contributors_url = []
        for contributor in node['contributors']:
            user = User.find(_id=contributor)
            if user is not None:
                contributors.append(user['fullname'])
                contributors_url.append('/profile/'+contributor)
        id = node['_b_node_parent']
        url = get_url(node)
        if NodeWikiPage.find(
                node=node['_id'], is_current=True, page_name='home') is not None and 'content' in NodeWikiPage.find(
                node=node['_id'], is_current=True):
            wiki = NodeWikiPage.find(
                node=node['_id'], is_current=True)['content']
            remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
            wiki = remove_re.sub('', wiki)
            html = markdown(wiki)
            wiki = ''.join(BeautifulSoup(html).findAll(text=True))
        else:
            wiki = None
        document = {
            'id': id,
            node['_id']+'_title': node['title'],
            node['_id']+'_category':node['category'],
            node['_id']+'_public':True,
            node['_id']+'_tags':node['tags'],
            node['_id']+'_description':node['description'],
            node['_id']+'_url':'/project/'+id+'/node/'+node['_id'],
            node['_id']+'_wiki':wiki,
            'contributors':contributors,
            'contributors_url': contributors_url,
        }
        if Node.find(_id=id, is_public=True) is not None:
            migrate_solr(document)

def find_parent(id, url=''):
    node = Node.find(_id=id)
    if node is not None and '_b_node_parent' in node:
        url = '/node/'+id+url
        return find_parent(Node.find(_id=node['_b_node_parent'])['_id'], url)
    else:
        url = '/project/'+id+url
        print '...and now the url is...', url
        return url

def find_root_id(id):
    node = Node.find(_id=id)
    if node is not None and '_b_node_parent' in node:
        return find_root_id(Node.find(_id=node['_b_node_parent'])['_id'])
    else:
        return id

def get_url(node):
    if node['category'] == 'project':
        return '/project/' + node['_id']
    else:
        return '/project/' + node['_b_node_parent'] + '/node/' + node['_id']


migrate_projects()
migrate_nodes()