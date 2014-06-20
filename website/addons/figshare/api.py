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
from utils import file_to_hgrid, article_to_hgrid
from website.util.sanitize import deep_clean


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
        self.last_error = None

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

    def _get_last_error(self):
        e = self.last_error
        self.last_error = None
        return e

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
            return deep_clean(rv)
        else:
            self.last_error = req.status_code
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
                return mapper(deep_clean(rv))
            elif callable(rv):
                return deep_clean(rv())
            return rv
        else:
            self.handle_error(req)

    # PROJECT LEVEL API
    def projects(self, node_settings):
        res = self._send(os.path.join(node_settings.api_url, 'projects'))
        return res

    def project(self, node_settings, project_id):
        if not project_id:
            return
        project = self._send(os.path.join(node_settings.api_url, 'projects', str(project_id)))
        if not project:
            return
        articles = self._send(
            os.path.join(node_settings.api_url, 'projects', "{0}".format(project_id), 'articles'))
        project['articles'] = []
        if(articles):
            project['articles'] = [self.article(node_settings, article['id'])['items'][0]
                                   for article in articles]
        return project

    def create_project(self, node_settings, project, description=''):
        data = json.dumps({"title": project, "description": description})
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

    # ARTICLE LEVEL API
    def articles(self, node_settings):
        articles = self._send(os.path.join(node_settings.api_url, 'articles'))
        articles = [self.article(node_settings, article['id']) for article in articles]
        return articles

    def article_is_public(self, article):
        res = requests.get(os.path.join(figshare_settings.API_URL,  'articles', str(article)))
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
        return article_to_hgrid(node_settings.owner, article)  # TODO Fix me

    def create_article(self, node_settings, article, d_type='paper'):
        body = json.dumps(
            {'title': article['title'], 'description': article.get('description') or '', 'defined_type': d_type})
        article.update(self._send_with_data(
            os.path.join(node_settings.api_url, 'articles'), method='post', data=body))
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

    def update_article(self, node_settings, article, params):
        return self._send(os.path.join(node_settings.api_url, 'articles', article, 'categories'), method='PUT', data=json.dumps(params), headers={'content-type': 'application/json'})

    def upload_file(self, node, node_settings, article, upload):
        #article_data = self.article(node_settings, article)['items'][0]
        filename, filestream = self.create_temp_file(upload)
        filedata = {
            'filedata': (filename, filestream)
        }
        response = self._send_with_data(
            os.path.join(node_settings.api_url, 'articles', str(article['article_id']), 'files'), method='put', output='json', files=filedata)

        filestream.close()

        return file_to_hgrid(node, article, response)

    def delete_article(self, node_settings, article):
        return self._send(os.path.join(node_settings.api_url, 'articles', article), method='delete')

    def publish_article(self, node_settings, article):
        res = self._send(os.path.join(node_settings.api_url, 'articles',
                         article, 'action', 'make_public'), method='post')
        return res

    # FILE LEVEL API
    def delete_file(self, node, node_settings, article_id, file_id):
        res = self._send(os.path.join(node_settings.api_url, 'articles',
                         article_id, 'files', file_id), method='delete')
        return res

    # OTHER HELPERS
    def get_options(self):
        projects = self._send("http://api.figshare.com/v1/my_data/projects")
        articles = self._send("http://api.figshare.com/v1/my_data/articles")

        if projects is False or articles is False:
            return self._get_last_error()

        return [{'label': project['title'], 'value': 'project_{0}'.format(project['id'])}
                for project in projects] + \
            [{'label': article['title'], 'value': 'fileset_{0}'.format(article['article_id'])}
             for article in articles['items'] if article['defined_type'] == 'fileset']

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

    # TODO Fix ME
    def has_crud(figshare_id, figshare_type):
        res = self._send(
            "http://api.figshare.com/v1/my_data/{0}s/{1}".format(figshare_type, figshare_id))
        if not res:
            return False
        return True

    def categories(self):
        return self._send("http://api.figshare.com/v1/categories")

    def handle_error(self, request):
        # TODO handle errors nicely
        return False
