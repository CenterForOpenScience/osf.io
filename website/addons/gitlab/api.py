import urllib
import requests
import itertools

import gitlab
import cachecontrol
from requests.adapters import HTTPAdapter

from website.addons.gitlab import settings as gitlab_settings
from website.addons.gitlab.exceptions import NotFoundError


# Initialize caches
https_cache = cachecontrol.CacheControlAdapter()
default_adapter = HTTPAdapter()


class GitLabClient(object):

    def __init__(self, external_account=None, access_token=None):

        self.access_token = getattr(external_account, 'oauth_key', None) or access_token

        if self.access_token:
            self.gitlab = gitlab.Gitlab(gitlab_settings.GITLAB_BASE_URL, oauth_token=self.access_token)
        else:
            self.gitlab = gitlab.Gitlab(gitlab_settings.GITLAB_BASE_URL)

    def user(self, user=None):
        """Fetch a user or the authenticated user.

        :param user: Optional GitLab user name; will fetch authenticated
            user if omitted
        :return dict: GitLab API response
        """
        return self.gitlab.currentuser()

    def repo(self, repo_id):
        """Get a single Github repo's info.

        :param str repo_id: GitLab repository id
        :return: Dict of repo information
            See #TODO: link gitlab docs
        """
        rv = self.gitlab.getproject(repo_id)

        if rv:
            return rv
        raise NotFoundError

    def repos(self):
        return self.gitlab.getprojects()

    def user_repos(self, user):
        return self.gitlab.getprojectsowned()

    def my_org_repos(self, permissions=None):
        return []
        # TODO
        #permissions = permissions or ['push']
        #return itertools.chain.from_iterable(
        #    team.iter_repos()
        #    for team in self.gh3.iter_user_teams()
        #    if team.permission in permissions
        #)

    def create_repo(self, repo, **kwargs):
        return self.gitlab.createproject(repo)

    def branches(self, repo_id, branch=None):
        """List a repo's branches or get a single branch (in a list).

        :param str user: GitLab user name
        :param str repo: GitLab repo name
        :param str branch: Branch name if getting a single branch
        :return: List of branch dicts
            http://developer.github.com/v3/repos/#list-branches
        """
        # TODO
        if branch:
            return self.gitlab.getbranch(repo_id, branch)

        return self.gitlab.getbranches(repo_id)

    # TODO: reimplement and test
    def starball(self, user, repo, repo_id, ref='master'):
        """Get link for archive download.

        :param str user: GitLab user name
        :param str repo: GitLab repo name
        :param str ref: Git reference
        :returns: tuple: Tuple of headers and file location
        """
        uri = "projects/{0}/repository/archive?sha={1}".format(repo_id, ref)

        request = self._get_api_request(uri)

        return request.headers, request.content

    def hooks(self, user, repo):
#TODO
        """List webhooks

        :param str user: GitLab user name
        :param str repo: GitLab repo name
        :return list: List of commit dicts from GitLab; see
            http://developer.github.com/v3/repos/hooks/#json-http
        """
       # return self.repo(user, repo).iter_hooks()
        return False

#TODO
    def add_hook(self, user, repo, name, config, events=None, active=True):
        """Create a webhook.

        :param str user: GitLab user name
        :param str repo: GitLab repo name
        :return dict: Hook info from GitLab: see see
            http://developer.github.com/v3/repos/hooks/#json-http
        """
#        try:
#            hook = self.repo(user, repo).create_hook(name, config, events, active)
#        except github3.GitLabError:
#            # TODO Handle this case - if '20 hooks' in e.errors[0].get('message'):
#            return None
#        else:
#            return hook
        return False

#TODO
    def delete_hook(self, user, repo, _id):
        """Delete a webhook.

        :param str user: GitLab user name
        :param str repo: GitLab repo name
        :return bool: True if successful, False otherwise
        :raises: NotFoundError if repo or hook cannot be located
        """
#        repo = self.repo(user, repo)
#        hook = repo.hook(_id)
#        if hook is None:
#            raise NotFoundError
#        return repo.hook(_id).delete()
        return False

    ########
    # Auth #
    ########

#TODO
    def revoke_token(self):
#        if self.access_token:
#            return self.gh3.revoke_authorization(self.access_token)
        return False


    def _get_api_request(self, uri):
        headers = {"Authorization": 'Bearer {}'.format(self.access_token)}

        return requests.get("{0}/{1}/{2}".format(gitlab_settings.GITLAB_BASE_URL, 'api/v3', uri),
                            verify=True, headers=headers)


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
