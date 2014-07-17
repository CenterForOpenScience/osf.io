# -*- coding: utf-8 -*-

import os
import base64

from website.models import NodeLog

from website.addons.base.services import fileservice

from website.addons.gitlab.api import client, GitlabError
from website.addons.gitlab import settings as gitlab_settings
from website.addons.gitlab import utils


def check_file_size(addon_model, filelike, at_end=False):
    if not at_end:
        filelike.seek(0, os.SEEK_END)
    size = filelike.tell()
    if size > addon_model.config.max_file_size * 1024 * 1024:
        raise fileservice.FileTooLargeError()


def create_or_update(addon_model, user_addon, path, content, branch):
    """

    :returns: Tuple of (action, response)
    :raises: FileUploadError if both create and update actions fail

    """
    payload = {
        'project_id': addon_model.project_id,
        'file_path': path,
        'branch_name': branch,
        'content': content,
        'commit_message': gitlab_settings.MESSAGES['add'],
        'encoding': 'base64',
        'user_id': user_addon.user_id,
    }
    try:
        return NodeLog.FILE_ADDED, client.createfile(**payload)
    except GitlabError:
        try:
            return NodeLog.FILE_UPDATED, client.updatefile(**payload)
        except GitlabError:
            raise fileservice.FileUploadError()


class ListBranchesError(fileservice.FileServiceError):
    pass


class ListCommitsError(fileservice.FileServiceError):
    pass


class GitlabFileService(fileservice.FileService):

    def upload(self, path, filelike, branch, user_addon):
        """

        :raises: FileTooLargeError, FileUploadError

        """
        content = filelike.read()

        check_file_size(self.addon_model, filelike, at_end=True)

        content = base64.b64encode(content)

        filename = os.path.join(
            path,
            utils.gitlab_slugify(filelike.filename),
        )

        return create_or_update(
            self.addon_model,
            user_addon,
            filename,
            content,
            branch=branch,
        )

    def download(self, path, ref):
        """

        :raises: FileDownloadError

        """
        try:
            contents = client.getfile(self.addon_model.project_id, path, ref)
            return base64.b64decode(contents['content'])
        except GitlabError:
            raise fileservice.FileDownloadError()

    def delete(self, path, branch):
        """

        :raises: FileDeleteError

        """
        try:
            client.deletefile(
                self.addon_model.project_id, path, branch,
                gitlab_settings.MESSAGES['delete']
            )
        except GitlabError:
            raise fileservice.FileDeleteError()

    def list_files(self, path, sha, branch):
        try:
            return client.listrepositorytree(
                self.addon_model.project_id,
                path=path,
                ref_name=sha or branch,
            )
        except GitlabError:
            raise fileservice.ListFilesError()

    def list_branches(self):
        """

        :raises: ListBranchesError

        """
        try:
            return client.listbranches(
                self.addon_model.project_id
            )
        except GitlabError:
            raise ListBranchesError()

    def list_commits(self, ref, path=None, **kwargs):
        """

        :param str ref: Git reference
        :param str path: Path to file; if ``None``, list commits for entire
            repo
        :param kwargs: Optional arguments to `listrepositorycommits`

        :raises: ListCommitsError

        """
        try:
            return client.listrepositorycommits(
                self.addon_model.project_id, ref_name=ref, path=path,
                **kwargs
            )
        except GitlabError:
            raise ListCommitsError()
