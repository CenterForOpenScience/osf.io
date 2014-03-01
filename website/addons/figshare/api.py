"""

"""

import os
import json
from urllib2 import urlopen
from re import search

from werkzeug.utils import secure_filename
from tempfile import TemporaryFile

import requests
from requests_oauthlib import OAuth1Session
from . import settings as figshare_settings


class Figshare(object):

    def __init__(self, client_token, client_secret, owner_token, owner_secret):
        # if no OAuth
        if owner_token is None:
            self.session = requests
        else:
            self.client_token = client_token
            self.client_secret = client_secret
            self.owner_token = owner_token
            self.owner_secret = owner_secret

            self.session = OAuth1Session(
                client_token,
                client_secret=client_secret,
                resource_owner_key=owner_token,
                resource_owner_secret=owner_secret,
                signature_type='auth_header'
            )

    @classmethod
    def from_settings(cls, settings):
        if settings is None or not hasattr(settings, 'oauth_access_token'):
            return cls(None, None, None, None)
        else:
            return cls(
                client_token=figshare_settings.CLIENT_ID,
                client_secret=figshare_settings.CLIENT_SECRET,
                owner_token=settings.oauth_access_token,
                owner_secret=settings.oauth_access_token_secret,
            )

    def _send(self, url, method='get', output='json', cache=True, **kwargs):
        """

        """
        func = getattr(self.session, method.lower())

        # Send request
        req = func(url, **kwargs)

        # Get return value
        rv = None
        if 200 <= req.status_code < 300:
            if output is None:
                rv = req
            else:
                rv = getattr(req, output)
                if callable(rv):
                    rv = rv()
            return rv
        else:
            return False

    def _send_with_data(self, url, method='post', output='json', **kwargs):
        mapper = kwargs.get('mapper')
        if mapper:
            del kwargs['mapper']

        files = kwargs.get('files')
        data = kwargs.get('data')

        func = getattr(self.session, method.lower())

        req = None

        headers = {}
        if data:
            headers = {'content-type': 'application/json'}
            req = func(url, headers=headers, **kwargs)
        elif files:
            req = func(url, **kwargs)
        if 200 <= req.status_code < 300:
            if output is None:
                return req
            rv = getattr(req, output)
            if mapper:
                return mapper(rv)
            elif callable(rv):
                return rv()
            return rv
        else:
            self.handle_error(req)

    # PROJECT LEVEL API
    def projects(self, node_settings):
        res = self._send(os.path.join(node_settings.api_url, 'projects'))
        return res

    def project(self, node_settings, project_id):
        project = self._send(os.path.join(node_settings.api_url, 'projects', project_id))
        articles = self._send(
            os.path.join(node_settings.api_url, 'projects', "{0}".format(project_id), 'articles'))
        if(articles):
            project['articles'] = [self.article(node_settings, article['id'])['items'][0]
                                   for article in articles]
            return project
        return []

    def create_project(self, node_settings, project):
        data = {"title": project['title'], "description": project['description']}
        return self._send(os.path.join(node_settings.api_url, 'projects'), data=data, method='post')

    def delete_project(self, node_settings, project):
        return self._send(os.path.join(node_settings.api_url, 'projects', project), method='delete')

    def add_article_to_project(self, node_settings, project, article):
        data = json.dumps({"article_id": article})
        return self._send(os.path.join(node_settings.api_url, 'projects', project, 'articles'), data=data, method='put')

    def remove_article_from_project(self, node_settings, project, article):
        data = json.dumps({"article_id": article})
        return self._send(os.path.join(node_settings.api_url, 'projects', project, 'articles'), data=data, method='delete')

    def get_project_collaborators(self, node_settings, project):
        return self._send(os.path.join(node_settings.api_url, 'projects', project, 'collaborators'))

    def project_to_hgrid(self, node, node_settings, project, contents=False):
        urls = {
            'upload':  node.api_url + 'figshare/project/{pid}/create/article/'.format(pid=project['id']),
            'delete': node.api_url + 'figshare/{article}/file/{id}/delete/',
            'fetch': '{base}figshare/hgrid/project/{pid}'.format(base=node.api_url, pid=project['id'])
        }
        permissions = {
            'edit': True,
            'view': True
        }
        # if no OAuth
        if node_settings.user_settings is None:
            urls['upload'] = ''
            urls['delete'] = ''
            permissions['edit'] = False
            permissions['view'] = False

        grid = [{
                'name': project['title'],
                'description': project['description'],
                'created': project['created'],
                'id': project['id'],
                'kind': 'folder',
                'children': [],
                'permissions': permissions,
                'urls': urls
                }]

        children = grid[0]['children']
        for article in project['articles']:
            children.append(self.article_to_hgrid(node, node_settings, article))
        if contents:
            return children

        return grid

    # ARTICLE LEVEL API
    def articles(self, node_settings):
        articles = self._send(os.path.join(node_settings.api_url, 'articles'))
        articles = [self.article(node_settings, article['id']) for article in articles]
        return articles

    def article_is_public(self, article):
        res = requests.get(os.path.join(figshare_settings.API_URL,  'articles', article))
        if res.status_code == 200:
            data = json.loads(res.content)
            if data['count'] == 0:
                return False
            elif data['items'][0]['status'] == 'Public':
                return True
        return False

    def article(self, node_settings, article_id):
        res = self._send(
            os.path.join(node_settings.api_url, 'articles', "{0}".format(article_id)))
        return res

    def article_version(self, node_settings, article_id, article_version):
        article = self._send(
            os.path.join(node_settings.api_url, 'articles', article_id, 'versions', article_version))
        return self.article_to_hgrid(article)

    def create_article(self, node_settings, article):
        body = json.dumps(
            {'title': article['title'], 'description': article['description']})
        article = self._send_with_data(
            os.path.join(node_settings.api_url, 'articles'), method='post', data=body)
        if article['files']:
            for f in article['files']:
                filename, filestream = create_temp_file(f)
                filedata = {
                    'filedata': (filename, filestream)
                }
                self._send_with_data(
                    os.path.join(node_settings.api_url, 'articles'), method='put', files=filedata)
                filestream.close()
        return self.article(node_settings, article['article_id'])

    def upload_file(self, node, node_settings, article, upload):
        article_data = self.article(node_settings, article)['items'][0]
        filename, filestream = self.create_temp_file(upload)
        filedata = {
            'filedata': (filename, filestream)
        }
        response = self._send_with_data(
            os.path.join(node_settings.api_url, 'articles', article, 'files'), method='put', output='json',
            mapper=lambda response: self.article_to_hgrid(
                node, node_settings, article_data),
            files=filedata)
        filestream.close()
        return response

    def delete_article(self, node_settings, article):
        return self._send(os.path.join(node_settings.api_url, 'articles', article), method='delete')

    def make_article_public(self, node_settings, article):
        return self._send(os.path.join(node_settings.api_url, 'articles', article, 'action', 'make_public'), method='post')

    # FILE LEVEL API
    def delete_file(self, node, node_settings, article_id, file_id):
        res = self._send(os.path.join(node_settings.api_url, 'articles',
                         article_id, 'files', file_id), method='delete')
        return res

    # HGRID OUTPUT
    def article_to_hgrid(self, node, node_settings, article, contents=False):

        a_fileset = (article['defined_type'] == 'fileset')

        children = []
        if a_fileset:
            for item in article.get('files') or []:
                children.append(
                    self.file_to_hgrid(node, node_settings, article, item, (article['status'] == 'Public')))

        # special case for hgrid lazyLoad
        if contents:
            return [children]

        urls = {
            'upload': '{base}figshare/create/article/{aid}/'.format(base=node.api_url, aid=article['article_id']),
            'delete': node.api_url + 'figshare/' + str(article['article_id']) + '/file/{id}/delete/',
            'download': '',
            'fetch': '{base}figshare/hgrid/article/{aid}'.format(base=node.api_url, aid=article['article_id']),
            'view': ''
        }
        permissions = {
            'edit': True if article['status'] == 'Public' else False,
            'view': True,
            'download': True if article['status'] == 'Public' else False
        }

        # if no OAuth
        if node_settings.user_settings is None:
            permissions['edit'] = False
            permissions['view'] = False
            permissions['download'] = False
            permissions['upload'] = a_fileset

        if not a_fileset:
            urls['download'] = article['files'][0].get('download_url')
            urls[
                'view'] = '{base}figshare/article/{aid}/file/{fid}'.format(base=node.api_url,
                                                                           aid=article['article_id'], fid=article['files'][0].get('id'))

        name = article['title'] if not article[
            'title'] == '' else '<em>untitled article</em>'
        kind = 'file' if not a_fileset else 'folder'

        article = {
            'name': name,
            'kind': kind,
            'published': article['published_date'],
            'tags': ', '.join([tag['name'] for tag in article['tags']]),
            'description': article['description_nohtml'],
            'authors': ', '.join([author['full_name'] for author in article['authors']]),
            'status': article['status'],
            'versions': article['version'],
            'urls':  urls,
            'permissions': permissions,
            'size': str(len(article['files'])),
            'indent': 0,
            'children': children
        }

        return article

    def file_to_hgrid(self, node, node_settings, article, item, public):
        urls = {
            'upload': '',
            'delete': '',
            # node.api_url+'figshare/'+str(article['article_id'])+'/file/{id}/delete/',
            'download': item.get('download_url'),
            'view': '{base}figshare/article/{aid}/file/{fid}'.format(base=node.api_url, aid=article['article_id'], fid=item.get('id'))
        }
        permissions = {
            'edit': False,
            'view': True,
            'download': True if public else False
        }

        gridfile = {
            'name': item['name'],
            'kind': 'file',
            'published': '',
            'tags': '',
            'description': '',
            'authors': '',
            'status': article['status'],
            'versions': '',
            'urls':  urls,
            'permissions': permissions,
            'size': item.get('size'),
            'indent': 1,
            'thumbnail': item.get('thumb') or '',
        }
        return gridfile

    def tree_to_hgrid(self, node, node_settings, target, which, contents=False):
        if which == 'article':
            article = self.article(node_settings, target)
            article = article['items'][0]
            return [self.article_to_hgrid(node, node_settings, article, contents)]
        elif which == 'project':
            project = self.project(node_settings, target)
            return self.project_to_hgrid(node, node_settings, project, contents)
        else:
            return []

    # OTHER HELPERS
    def get_options(self):
        projects = self._send("http://api.figshare.com/v1/my_data/projects")
        projects = map(lambda project:
                       {'label': project['title'], 'value': 'project_' + str(project['id'])}, projects)
        articles = self._send('http://api.figshare.com/v1/my_data/articles')
        articles = map(lambda article: {
                       'label': article['title'], 'value': 'article_' + str(article['article_id'])}, articles['items'])
        return json.dumps(projects + articles)

    def get_file(self, node_settings, found):
        url = found.get('download_url')
        if not url:
            return None, None
        f = urlopen(url)
        filedata = f.read()
        f.close()
        size = found['size']
        size = int(search(r'(\d+)\s?(\w)', size).group(1)) or 0
        return found['name'], size, filedata

    def create_temp_file(self, upload):
        filename = secure_filename(upload.filename)
        f = TemporaryFile('w+b')
        f.write(upload.read())
        f.seek(0)
        return filename, f

    #TODO Fix ME
    def has_crud(figshare_id, figshare_type):
        res = self._send(
            "http://api.figshare.com/v1/my_data/{0}s/{1}".format(figshare_type, figshare_id))
        if not res:
            return False
        return True

    def handle_error(self, request):
        # TODO handle errors nicely
        return False
