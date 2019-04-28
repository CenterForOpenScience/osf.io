import urllib

from addons.bitbucket import settings

from framework import sentry
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
        res = self._make_request(
            'GET',
            self._build_url(settings.BITBUCKET_V2_API_URL, 'repositories', self.username),
            expects=(200, ),
            throws=HTTPError(401),
            params={'pagelen': 100}
        )
        repo_list = res.json()['values']

        # GDPR docs: https://developer.atlassian.com/cloud/bitbucket/bitbucket-api-changes-gdpr/
        #
        # The GDPR guide is quite ambiguous on "removal of username".  It mentions that this change
        # should only affect the ``/2.0/users/`` endpoint but also says that the ``username`` field
        # will be removed from the ``User`` object.  Without an explicit exception statement, we are
        # not quite certain that each repository object in the response will continue to provide the
        # ``owner.username``.  This attribute is used to 1) Set the ``user`` field for the addon's
        # ``node_settings`` and 2) to build the repo URL during addon configuration.  The config
        # would break if ``username`` is gone.  If it happened, we can apply a few fixes including
        # 1) replacing ``owner.username`` with ``owner.account_id``, 2) using the ``display_name``
        # of the ``ExternalAccount`` model, and 3) using one of the repo URL links in the response.
        #
        # Added the following check and sentry log to make sure that we would be informed of the
        # failure if it happened after the GDPR update.  Checking the first itme should be good.
        for repo in repo_list:
            username = repo['owner'].get('username', None)
            if not username:
                sentry.log_message('WARNING: Bitbucket V2 "repositories/user" no '
                                   'longer returns required field "owner.username".')
            break

        return repo_list

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
            throws=HTTPError(401),
            params={'pagelen': 100}
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

    params = urllib.urlencode({
        key: value
        for key, value in {'branch': branch, 'sha': sha}.items()
        if value
    })
    if params:
        return '?' + params
    return ''
