import urllib
# import itertools

from framework.exceptions import HTTPError

from website.util.client import BaseClient
from website.addons.bitbucket import settings


class BitbucketClient(BaseClient):

    def __init__(self, access_token=None):
        self.access_token = access_token
        self.username = None

    @property
    def _default_headers(self):
        if self.access_token:
            return {'Authorization': 'Bearer {}'.format(self.access_token)}
        return {}

    def get_username(self):
        if not self.username:
            self.username = self.get_user()['username']
        return self.username

    def get_user(self):
        """Fetch the user identified by ``self.access_token``.

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/user

        :rtype: dict
        :return: a metadata object representing the user
        """
        res = self._make_request(
            'GET',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'user'),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def user(self, username=None):
        """Fetch a user or the authenticated user.

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/users

        :param user: Optional Bitbucket user name; will fetch authenticated
            user if omitted
        :rtype: dict
        :return: user metadata object
        """
        if username is None:
            username = self.get_username

        res = self._make_request(
            'GET',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'users', username),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def repo(self, user, repo):
        """Get a single Bitbucket repo's info.

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D/%7Brepo_slug%7D

        :param str user: Bitbucket user name
        :param str repo: Bitbucket repo name
        :return: Dict of repo information
            See http://developer.bitbucket.com/v3/repos/#get
        """
        res = self._make_request(
            'GET',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'repositories', user, repo),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def repos(self):
        """Return a list of repository objects owned by the user

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D

        :rtype:
        :return: list of repository objects
        """
        res = self._make_request(
            'GET',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'repositories', self.get_username()),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()['values']

    def team_repos(self):
        """Return a list of repositories owned by teams the user is a member of.

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/teams

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/teams/%7Busername%7D/repositories

        :rtype: list
        :return: a list of repository objects
        """

        res = self._make_request(
            'GET',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'teams') + '?role=member',
            expects=(200, ),
            throws=HTTPError(401)
        )
        teams = [x['username'] for x in res.json()['values']]

        team_repos = []
        for team in teams:
            res = self._make_request(
                'GET',
                self._build_url(settings.BITBUCKET_V2_API_URL, 'teams', team, 'repositories'),
                expects=(200, ),
                throws=HTTPError(401)
            )
            team_repos.extend(res.json()['values'])

        return team_repos

    def get_repo_default_branch(self, user, repo):
        """Return the default branch for a BB repository (what they call the
        "main branch").  They do not provide this via their v2 API,
        but there is a v1 endpoint that will return it.

        API doc:
        https://confluence.atlassian.com/bitbucket/repository-resource-1-0-296095202.html#repositoryResource1.0-GETtherepository%27smainbranch

        :param str user: Bitbucket user name
        :param str repo: Bitbucket repo name
        :rtype str:
        :return: name of the main branch

        """
        res = self._make_request(
            'GET',
            self._build_url(settings.BITBUCKET_V1_API_URL, 'repositories', user, repo, 'main-branch'),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()['name']

    def branches(self, user, repo):
        """List a repo's branches.  This endpoint is paginated and may require
        multiple requests.

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D/%7Brepo_slug%7D/refs/branches

        :param str user: Bitbucket user name
        :param str repo: Bitbucket repo name
        :return: List of branch dicts
        """
        branches, page_nbr = [], 1
        while True:
            url = self._build_url(settings.BITBUCKET_V2_API_URL, 'repositories', user, repo,
                                  'refs', 'branches')
            url = '{}?page={}'.format(url, page_nbr)
            res = self._make_request(
                'GET',
                url,
                expects=(200, ),
                throws=HTTPError(401)
            )
            res_data = res.json()
            branches.extend(res_data['values'])
            page_nbr += 1
            if not res_data.get('next', None):
                break
        return branches

    #########
    # Hooks #
    #########

    def hooks(self, username, repo):
        """List webhooks on a repo

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D/%7Brepo_slug%7D/hooks

        :param str username: Bitbucket user name
        :param str repo: Bitbucket repo name
        :return list: List of commit dicts from Bitbucket; see
            http://developer.bitbucket.com/v3/repos/hooks/#json-http
        """
        if username is None:
            username = self.get_username

        res = self._make_request(
            'GET',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'repositories', username, repo, 'hooks'),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()

    def add_hook(self, username, repo, config):
        """Create a webhook.

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D/%7Brepo_slug%7D/hooks#post

        :param str username: Bitbucket user name
        :param str repo: Bitbucket repo name
        :param dict config: a dictionary describing the hook configuration. See api docs.
        :return dict: Hook info from Bitbucket. See docs.
        """
        if username is None:
            username = self.get_username

        res = self._make_request(
            'POST',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'repositories', username,
                            repo, 'hooks'),
            config,
            expects=(201, ),
            throws=HTTPError(401)
        )
        return res.json()

    def delete_hook(self, username, repo, _id):
        """Delete a webhook.

        API Docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D/%7Brepo_slug%7D/hooks/%7Buid%7D#delete

        :param str username: Bitbucket user name
        :param str repo: Bitbucket repo name
        :param str _id: id of webhook to delete
        :return bool: True if successful, False otherwise
        :raises: NotFoundError if repo or hook cannot be located
        """
        if username is None:
            username = self.get_username

        res = self._make_request(
            'DELETE',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'repositories', username,
                            repo, 'hooks', _id),
            expects=(200, 404, ),
            throws=HTTPError(401)
        )
        return res.status == 200

def ref_to_params(branch=None, sha=None):

    params = urllib.urlencode({
        key: value
        for key, value in {'branch': branch, 'sha': sha}.iteritems()
        if value
    })
    if params:
        return '?' + params
    return ''
