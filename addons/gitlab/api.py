from future.moves.urllib.parse import urlencode
import requests

import gitlab
import cachecontrol
from requests.adapters import HTTPAdapter

from addons.gitlab.exceptions import NotFoundError, AuthError
from addons.gitlab.settings import DEFAULT_HOSTS

# Initialize caches
https_cache = cachecontrol.CacheControlAdapter()
default_adapter = HTTPAdapter()

class GitLabClient(object):

    def __init__(self, external_account=None, access_token=None, host=None):
        self.access_token = getattr(external_account, 'oauth_key', None) or access_token
        self.host = getattr(external_account, 'oauth_secret', None) or host or DEFAULT_HOSTS[0]

        if self.access_token:
            self.gitlab = gitlab.Gitlab(self.host, private_token=self.access_token)
        else:
            self.gitlab = gitlab.Gitlab(self.host)

    def user(self, user=None):
        """Fetch a user or the authenticated user.

        :param user: Optional GitLab user name; will fetch authenticated
            user if omitted
        :return dict: GitLab API response
        """
        try:
            self.gitlab.auth()
        except gitlab.GitlabGetError as exc:
            raise AuthError(exc.error_message)

        return self.gitlab.users.get(self.gitlab.user.id)

    def repo(self, repo_id):
        """Get a single GitLab repo's info.

        https://docs.gitlab.com/ce/api/projects.html#get-single-project

        :param str repo_id: GitLab repository id
        :return: gitlab.Project a object representing the repo
        """

        try:
            return gitlab.Project(self.gitlab, repo_id)
        except gitlab.GitlabGetError as exc:
            if exc.response_code == 404:
                raise NotFoundError
            else:
                raise exc

    def repos(self):
        return self.gitlab.projects.list(membership=True)

    def branches(self, repo_id, branch=None):
        """List a repo's branches or get a single branch (in a list).

        https://docs.gitlab.com/ce/api/branches.html#list-repository-branches

        :param str user: GitLab user name
        :param str repo: GitLab repo name
        :param str branch: Branch name if getting a single branch
        :return: List of branch dicts
        """
        if branch:
            return gitlab.Project(self.gitlab, repo_id).branches.get(branch)

        return gitlab.Project(self.gitlab, repo_id).branches.list()

    def starball(self, user, repo, repo_id, ref='master'):
        """Get link for archive download.

        :param str user: GitLab user name
        :param str repo: GitLab repo name
        :param str ref: Git reference
        :returns: tuple: Tuple of headers and file location
        """
        uri = 'projects/{0}/repository/archive?sha={1}'.format(repo_id, ref)

        request = self._get_api_request(uri)

        return request.headers, request.content

    def hooks(self, user, repo):
        """List webhooks

        https://docs.gitlab.com/ce/api/projects.html#list-project-hooks

        :param str user: GitLab user name
        :param str repo: GitLab repo name
        :return list: List of commit dicts from GitLab; see
        """
        return False

    def add_hook(self, user, repo, name, config, events=None, active=True):
        """Create a webhook.

        https://docs.gitlab.com/ce/api/projects.html#add-project-hook

        :param str user: GitLab user name
        :param str repo: GitLab repo name
        :return dict: Hook info from GitLab: see see
        """
        return False

    def delete_hook(self, user, repo, _id):
        """Delete a webhook.

        https://docs.gitlab.com/ce/api/projects.html#delete-project-hook

        :param str user: GitLab user name
        :param str repo: GitLab repo name
        :return bool: True if successful, False otherwise
        :raises: NotFoundError if repo or hook cannot be located
        """
        return False

    def _get_api_request(self, uri):
        headers = {'PRIVATE-TOKEN': '{}'.format(self.access_token)}

        return requests.get('https://{0}/{1}/{2}'.format(self.host, 'api/v4', uri),
                            verify=True, headers=headers)

    def revoke_token(self):
        return False


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
