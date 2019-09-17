from future.moves.urllib.parse import urlencode

from addons.bitbucket import settings

from framework.exceptions import HTTPError

from website.util.client import BaseClient


class BitbucketClient(BaseClient):

    def __init__(self, access_token=None):
        self.access_token = access_token

    @property
    def _default_headers(self):
        if self.access_token:
            return {'Authorization': 'Bearer {}'.format(self.access_token)}
        return {}

    @property
    def username(self):
        return self.user()['username']

    def user(self):
        """Fetch the user identified by ``self.access_token``.

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/user

        Bitbucket API GDPR Update::

        * https://developer.atlassian.com/cloud/bitbucket/bitbucket-api-changes-gdpr/

        As mentioned in the GDPR update on "removal of username", the ``/2.0/user`` endpoint will
        continue to provide the ``username`` field in its response since this endpoint only ever
        returns the authenticated user's own user object, not that of other users.

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

    def repo(self, user, repo):
        """Get a single Bitbucket repo's info.

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D/%7Brepo_slug%7D

        :param str user: Bitbucket user name
        :param str repo: Bitbucket repo name
        :return: Dict of repo information
        """
        res = self._make_request(
            'GET',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'repositories', user, repo),
            expects=(200, 404, ),
            throws=HTTPError(401)
        )
        return None if res.status_code == 404 else res.json()

    def repos(self):
        """Return a list of repository objects owned by the user

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D

        :rtype:
        :return: list of repository objects
        """
        query_params = {
            'pagelen': 100,
            'fields': 'values.full_name'
        }
        res = self._make_request(
            'GET',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'repositories', self.username),
            expects=(200, ),
            throws=HTTPError(401),
            params=query_params
        )
        repo_list = res.json()['values']

        return repo_list

    def team_repos(self):
        """Return a list of repositories owned by teams the user is a member of.

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/teams

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/teams/%7Busername%7D/repositories

        :rtype: list
        :return: a list of repository objects
        """

        query_params = {
            'role': 'member',
            'pagelen': 100,
            'fields': 'values.links.repositories.href'
        }
        res = self._make_request(
            'GET',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'teams'),
            expects=(200, ),
            throws=HTTPError(401),
            params=query_params
        )
        team_repos_url_list = [x['links']['repositories']['href'] for x in res.json()['values']]

        team_repos = []
        for team_repos_url in team_repos_url_list:
            res = self._make_request(
                'GET',
                team_repos_url,
                expects=(200, ),
                throws=HTTPError(401),
                params={'fields': 'values.full_name'}
            )
            team_repos.extend(res.json()['values'])

        return team_repos

    def repo_default_branch(self, user, repo):
        """Return the default branch for a BB repository (what they call the
        "main branch").

        API doc:
        https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D/%7Brepo_slug%7D

        :param str user: Bitbucket user name
        :param str repo: Bitbucket repo name
        :rtype str:
        :return: name of the main branch

        """
        res = self._make_request(
            'GET',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'repositories', user, repo),
            expects=(200, ),
            throws=HTTPError(401)
        )
        return res.json()['mainbranch']['name']

    def branches(self, user, repo):
        """List a repo's branches.  This endpoint is paginated and may require
        multiple requests.

        API docs::

        * https://developer.atlassian.com/bitbucket/api/2/reference/resource/repositories/%7Busername%7D/%7Brepo_slug%7D/refs/branches

        :param str user: Bitbucket user name
        :param str repo: Bitbucket repo name
        :return: List of branch dicts
        """
        branches = []
        url = self._build_url(settings.BITBUCKET_V2_API_URL, 'repositories', user, repo, 'refs', 'branches')
        while True:
            res = self._make_request(
                'GET',
                url,
                expects=(200, ),
                throws=HTTPError(401)
            )
            res_data = res.json()
            branches.extend(res_data['values'])
            url = res_data.get('next', None)
            if not url:
                break
        return branches


def ref_to_params(branch=None, sha=None):

    params = urlencode({
        key: value
        for key, value in {'branch': branch, 'sha': sha}.items()
        if value
    })
    if params:
        return '?' + params
    return ''
