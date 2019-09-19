from framework.exceptions import HTTPError

from website.util.client import BaseClient

from addons.figshare import settings


class FigshareClient(BaseClient):

    def __init__(self, access_token):
        self.access_token = access_token

    @classmethod
    def from_account(cls, account):
        if account is None:
            return cls(None)
        else:
            return cls(account.oauth_key)

    @property
    def _default_headers(self):
        if self.access_token:
            return {'Authorization': 'token {}'.format(self.access_token)}
        return {}

    @property
    def _default_params(self):
        return {'page_size': 100}

    def userinfo(self):
        return self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'account'),
            expects=(200, ),
            throws=HTTPError(403)
        ).json()

    # PROJECT LEVEL API
    def projects(self):
        return self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'account', 'projects')
        ).json()

    def project(self, project_id):
        if not project_id:
            return
        project = self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'account', 'projects', project_id),
            expects=(200,)
        ).json()
        if not project:
            return
        articles = self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'account', 'projects', project_id, 'articles')
        ).json()
        project['articles'] = []
        if(articles):
            project['articles'] = []
            for article in articles:
                fetched = self.article(article['id'])
                if fetched:
                    project['articles'].append(fetched)
        return project

    # ARTICLE LEVEL API
    def articles(self, only_folders=False):
        article_list = self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'account', 'articles')
        ).json()
        if only_folders:
            article_list = [x for x in article_list
                            if x['defined_type'] in settings.FIGSHARE_FOLDER_TYPES]
        return [self.article(article['id']) for article in article_list]

    def article_is_public(self, article_id):
        return self.article(article_id).get('is_public')

    def project_is_public(self, project_id):
        return bool(self.project(project_id).get('date_published'))

    def container_is_public(self, container_id, container_type):
        if container_type == 'project':
            return self.project_is_public(container_id)
        elif container_id in settings.FIGSHARE_FOLDER_TYPES:
            return self.article_is_public(container_id)

    def article(self, article_id):
        return self._make_request(
            'GET',
            self._build_url(settings.API_BASE_URL, 'account', 'articles', article_id),
            expects=(200, )
        ).json()

    # OTHER HELPERS
    def get_folders(self):
        """ Return a list containing both projects and folder-like articles. """

        projects = self.projects()
        project_list = [
            {
                'name': project['title'],
                'path': 'project',
                'id': str(project['id']),
                'kind': 'folder',
                'permissions': {'view': True},
                'addon': 'figshare',
                'hasChildren': False
            } for project in projects
        ]

        article_list = [
            {
                'name': (article['title'] or 'untitled article'),
                'path': settings.FIGSHARE_IDS_TO_TYPES[article['defined_type']],
                'id': str(article['id']),
                'kind': 'folder',
                'permissions': {'view': True},
                'addon': 'figshare',
                'hasChildren': False
            } for article in self.articles(only_folders=True)
        ]

        return project_list + article_list

    def get_linked_folder_info(self, _id):
        """ Returns info about a linkable object -- 'project', 'dataset', or 'fileset' """
        ret = {}
        try:
            folder = self._make_request(
                'GET',
                self._build_url(settings.API_BASE_URL, 'account', 'projects', _id),
                expects=(200, ),
                throws=HTTPError(404)
            ).json()
            ret['path'] = 'project'
        except HTTPError:
            folder = self.article(_id)
            if folder.get('defined_type') not in settings.FIGSHARE_FOLDER_TYPES:
                raise
            ret['path'] = settings.FIGSHARE_IDS_TO_TYPES[folder.get('defined_type')]
        ret['name'] = folder['title'] or 'untitled article'
        ret['id'] = str(_id)
        return ret
