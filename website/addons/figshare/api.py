import os
import json

import requests
from requests_oauthlib import OAuth1Session

from website.util.sanitize import escape_html

from . import settings as figshare_settings


def _get_project_url(node_settings, project, *args):
    return os.path.join(node_settings.api_url, 'projects', str(project), *args)

class Figshare(object):

    def __init__(self, client_token=None, client_secret=None, owner_token=None, owner_secret=None):
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
                client_token=figshare_settings.CLIENT_ID or '',
                client_secret=figshare_settings.CLIENT_SECRET or '',
                owner_token=settings.oauth_access_token or '',
                owner_secret=settings.oauth_access_token_secret or '',
            )

    def _get_last_error(self):
        e = self.last_error
        self.last_error = None
        return e

    def _send(self, url, method='get', output='json', cache=True, **kwargs):
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
            return escape_html(rv)
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
                return mapper(escape_html(rv))
            elif callable(rv):
                return escape_html(rv())
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
            os.path.join(node_settings.api_url, 'projects', '{0}'.format(project_id), 'articles'))
        project['articles'] = []
        if(articles):
            project['articles'] = []
            for article in articles:
                fetched = self.article(node_settings, article['id'])
                if fetched:
                    project['articles'].append(fetched['items'][0])
        return project

    # ARTICLE LEVEL API
    def articles(self, node_settings):
        articles = self._send(os.path.join(node_settings.api_url, 'articles'))
        if not articles:
            return [], self.last_error
        articles = [self.article(node_settings, article['article_id']) for article in articles['items']]
        return articles, 200

    def article_is_public(self, article):
        res = requests.get(os.path.join(figshare_settings.API_URL, 'articles', str(article)))
        if res.status_code == 200:
            data = json.loads(res.content)
            if data['count'] == 0:
                return False
            elif data['items'][0]['status'] == 'Public':
                return True
        return False

    def article(self, node_settings, article_id):
        res = self._send(
            os.path.join(node_settings.api_url, 'articles', '{0}'.format(article_id)))
        return res

    # OTHER HELPERS
    def get_options(self):
        projects = self._send('http://api.figshare.com/v1/my_data/projects')
        articles = self._send('http://api.figshare.com/v1/my_data/articles')
        if projects is False or articles is False:
            return self._get_last_error()

        return [{'label': project['title'], 'value': 'project_{0}'.format(project['id'])}
                for project in projects] + \
            [{'label': (article['title'] or 'untitled article'), 'value': 'fileset_{0}'.format(article['article_id'])}
             for article in articles['items'] if article['defined_type'] == 'fileset']

    def categories(self):
        return self._send('http://api.figshare.com/v1/categories')

    def handle_error(self, request):
        # TODO handle errors nicely
        return False
