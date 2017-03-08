import urllib
import itertools

import bitbucket3
import cachecontrol
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError

from website.addons.bitbucket import settings as bitbucket_settings
from website.addons.bitbucket.exceptions import NotFoundError


# Initialize caches
https_cache = cachecontrol.CacheControlAdapter()
default_adapter = HTTPAdapter()


class BitbucketClient(object):

    def __init__(self, external_account=None, access_token=None):

        self.access_token = getattr(external_account, 'oauth_key', None) or access_token
        if self.access_token:
            self.gh3 = bitbucket3.login(token=self.access_token)
            self.gh3.set_client_id(
                bitbucket_settings.CLIENT_ID, bitbucket_settings.CLIENT_SECRET
            )
        else:
            self.gh3 = bitbucket3.Bitbucket()

        # Caching libary
        if bitbucket_settings.CACHE:
            self.gh3._session.mount('https://api.bitbucket.com/user', default_adapter)
            self.gh3._session.mount('https://', https_cache)

    def user(self, user=None):
        """Fetch a user or the authenticated user.

        :param user: Optional Bitbucket user name; will fetch authenticated
            user if omitted
        :return dict: Bitbucket API response
        """
        return self.gh3.user(user)

    def repo(self, user, repo):
        """Get a single Bitbucket repo's info.

        :param str user: Bitbucket user name
        :param str repo: Bitbucket repo name
        :return: Dict of repo information
            See http://developer.bitbucket.com/v3/repos/#get
        """
        try:
            rv = self.gh3.repository(user, repo)
        except ConnectionError:
            raise NotFoundError

        if rv:
            return rv
        raise NotFoundError

    def repos(self):
        return self.gh3.iter_repos(type='all', sort='full_name')

    def user_repos(self, user):
        return self.gh3.iter_user_repos(user, type='all', sort='full_name')

    def my_org_repos(self, permissions=None):
        permissions = permissions or ['push']
        return itertools.chain.from_iterable(
            team.iter_repos()
            for team in self.gh3.iter_user_teams()
            if team.permission in permissions
        )

    def create_repo(self, repo, **kwargs):
        return self.gh3.create_repo(repo, **kwargs)

    def branches(self, user, repo, branch=None):
        """List a repo's branches or get a single branch (in a list).

        :param str user: Bitbucket user name
        :param str repo: Bitbucket repo name
        :param str branch: Branch name if getting a single branch
        :return: List of branch dicts
            http://developer.bitbucket.com/v3/repos/#list-branches
        """
        if branch:
            return [self.repo(user, repo).branch(branch)]
        return self.repo(user, repo).iter_branches() or []

    # TODO: Test
    def starball(self, user, repo, archive='tar', ref='master'):
        """Get link for archive download.

        :param str user: Bitbucket user name
        :param str repo: Bitbucket repo name
        :param str archive: Archive format [tar|zip]
        :param str ref: Git reference
        :returns: tuple: Tuple of headers and file location
        """

        # bitbucket3 archive method writes file to disk
        repository = self.repo(user, repo)
        url = repository._build_url(archive + 'ball', ref, base_url=repository._api)
        resp = repository._get(url, allow_redirects=True, stream=True)

        return resp.headers, resp.content

    #########
    # Hooks #
    #########

    def hooks(self, user, repo):
        """List webhooks

        :param str user: Bitbucket user name
        :param str repo: Bitbucket repo name
        :return list: List of commit dicts from Bitbucket; see
            http://developer.bitbucket.com/v3/repos/hooks/#json-http
        """
        return self.repo(user, repo).iter_hooks()

    def add_hook(self, user, repo, name, config, events=None, active=True):
        """Create a webhook.

        :param str user: Bitbucket user name
        :param str repo: Bitbucket repo name
        :return dict: Hook info from Bitbucket: see see
            http://developer.bitbucket.com/v3/repos/hooks/#json-http
        """
        try:
            hook = self.repo(user, repo).create_hook(name, config, events, active)
        except bitbucket3.BitbucketError:
            # TODO Handle this case - if '20 hooks' in e.errors[0].get('message'):
            return None
        else:
            return hook

    def delete_hook(self, user, repo, _id):
        """Delete a webhook.

        :param str user: Bitbucket user name
        :param str repo: Bitbucket repo name
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


def ref_to_params(branch=None, sha=None):

    params = urllib.urlencode({
        key: value
        for key, value in {
            'branch': branch,
            'sha': sha,
        }.iteritems()
        if value
    })
    if params:
        return '?' + params
    return ''
