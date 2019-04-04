from future.moves.urllib.parse import urlencode

import github3
import cachecontrol
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError

from addons.github import settings as github_settings
from addons.github.exceptions import NotFoundError


# Initialize caches
https_cache = cachecontrol.CacheControlAdapter()
default_adapter = HTTPAdapter()


class GitHubClient(object):

    def __init__(self, external_account=None, access_token=None):

        self.access_token = getattr(external_account, 'oauth_key', None) or access_token
        if self.access_token:
            self.gh3 = github3.login(token=self.access_token)
            self.gh3.set_client_id(
                github_settings.CLIENT_ID, github_settings.CLIENT_SECRET
            )
        else:
            self.gh3 = github3.GitHub()

        # Caching libary
        if github_settings.CACHE:
            self.gh3._session.mount('https://api.github.com/user', default_adapter)
            self.gh3._session.mount('https://', https_cache)

    def user(self, user=None):
        """Fetch a user or the authenticated user.

        :param user: Optional GitHub user name; will fetch authenticated
            user if omitted
        :return dict: GitHub API response
        """
        if user is None:
            return self.gh3.me()
        return self.gh3.user(user)

    def repo(self, user, repo):
        """Get a single Github repo's info.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :return: Dict of repo information
            See http://developer.github.com/v3/repos/#get
        """
        try:
            rv = self.gh3.repository(user, repo)
        except ConnectionError:
            raise NotFoundError

        if rv:
            return rv
        raise NotFoundError

    def repos(self):
        repos = self.gh3.repositories(type='all', sort='pushed')
        return [repo for repo in repos if repo.permissions['push']]

    def create_repo(self, repo, **kwargs):
        return self.gh3.create_repository(repo, **kwargs)

    def branches(self, user, repo, branch=None):
        """List a repo's branches or get a single branch (in a list).

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str branch: Branch name if getting a single branch
        :return: List of branch dicts
            http://developer.github.com/v3/repos/#list-branches
        """
        if branch:
            return [self.repo(user, repo).branch(branch)]
        return self.repo(user, repo).branches() or []

    # TODO: Test
    def starball(self, user, repo, archive='tar', ref='master'):
        """Get link for archive download.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :param str archive: Archive format [tar|zip]
        :param str ref: Git reference
        :returns: tuple: Tuple of headers and file location
        """

        # github3 archive method writes file to disk
        repository = self.repo(user, repo)
        url = repository._build_url(archive + 'ball', ref, base_url=repository._api)
        resp = repository._get(url, allow_redirects=True, stream=True)

        return resp.headers, resp.content

    #########
    # Hooks #
    #########

    def hooks(self, user, repo):
        """List webhooks

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :return list: List of commit dicts from GitHub; see
            http://developer.github.com/v3/repos/hooks/#json-http
        """
        return self.repo(user, repo).hooks()

    def add_hook(self, user, repo, name, config, events=None, active=True):
        """Create a webhook.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :return dict: Hook info from GitHub: see see
            http://developer.github.com/v3/repos/hooks/#json-http
        """
        try:
            hook = self.repo(user, repo).create_hook(name, config, events, active)
        except github3.GitHubError:
            # TODO Handle this case - if '20 hooks' in e.errors[0].get('message'):
            return None
        else:
            return hook

    def delete_hook(self, user, repo, _id):
        """Delete a webhook.

        :param str user: GitHub user name
        :param str repo: GitHub repo name
        :return bool: True if successful, False otherwise
        :raises: NotFoundError if repo or hook cannot be located
        """
        repo = self.repo(user, repo)
        hook = repo.hook(_id)
        if hook is None:
            raise NotFoundError
        return repo.hook(_id).delete()

    ########
    # Auth #
    ########

    def revoke_token(self):
        if self.access_token:
            return self.gh3.revoke_authorization(self.access_token)

    def check_authorization(self):
        return self.gh3.check_authorization(self.access_token)


def ref_to_params(branch=None, sha=None):

    params = urlencode({
        key: value
        for key, value in {
            'branch': branch,
            'sha': sha,
        }.items()
        if value
    })
    if params:
        return '?' + params
    return ''
