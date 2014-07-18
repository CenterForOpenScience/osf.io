# -*- coding: utf-8 -*-

import logging

from website.addons.base import AddonError

from website.addons.base.services.base import ServiceConfigurationError

from website.addons.gitlab.services import projectservice, fileservice


logger = logging.getLogger(__name__)


def ref_or_default(node_settings, data):
    """Get the git reference (SHA or branch) from view arguments; return the
    default reference if none is supplied.

    :param GitlabNodeSettings node_settings: Gitlab node settings
    :param dict data: View arguments
    :returns: SHA or branch if reference found, else None

    """
    return (
        data.get('sha')
        or data.get('branch')
        or get_default_branch(node_settings)
    )


def get_default_file_sha(node_settings, path, branch=None):
    file_service = fileservice.GitlabFileService(node_settings)
    try:
        commits = file_service.list_commits(branch, path)
    except (ServiceConfigurationError, fileservice.ListCommitsError):
        raise AddonError('Could not fetch commits')
    return commits[0]['id']


def get_default_branch(node_settings):
    """Get default branch of GitLab project.

    :param GitlabNodeSettings node_settings: Node settings object
    :returns: Name of default branch

    """
    project_service = projectservice.GitlabProjectService(node_settings)
    try:
        project = project_service.get()
    except (ServiceConfigurationError, projectservice.ProjectServiceError):
        raise AddonError('Could not fetch project')
    return project['default_branch']


def get_branch_id(node_settings, branch):
    """Get latest commit SHA for branch of GitLab project.

    :param GitlabNodeSettings node_settings: Node settings object
    :param str branch: Branch name
    :returns: SHA of branch

    """
    file_service = fileservice.GitlabFileService(node_settings)
    try:
        branch_json = file_service.list_branch(branch)
    except (ServiceConfigurationError, fileservice.ListBranchError):
        raise AddonError('Could not fetch branch')
    return branch_json['commit']['id']


def get_default_branch_and_sha(node_settings):
    """Get default branch and SHA for GitLab project.

    :param GitlabNodeSettings node_settings: Node settings object
    :returns: Tuple of (branch, SHA)

    """
    from website.addons.gitlab.services import fileservice
    file_service = fileservice.GitlabFileService(node_settings)
    branches_json = file_service.list_branches()
    if len(branches_json) == 1:
        branch = branches_json[0]['name']
        sha = branches_json[0]['commit']['id']
    else:
        branch = get_default_branch(node_settings)
        branch_json = [
            each
            for each in branches_json
            if each['name'] == branch
        ]
        if not branch_json:
            raise AddonError('Could not find branch')
        sha = branch_json[0]['commit']['id']
    return branch, sha


def get_branch_and_sha(node_settings, data):
    """Get branch and SHA from dictionary of view data.

    :param GitlabNodeSettings node_settings: Node settings
    :param dict data: Dictionary of view data; `branch` and `sha` keys will
        be checked
    :returns: Tuple of (branch, SHA)
    :raises: ValueError if SHA but not branch provided

    """
    branch = data.get('branch')
    sha = data.get('sha')

    # Can't infer branch from SHA
    if sha and not branch:
        raise ValueError('Cannot provide sha without branch')

    if sha is None:
        if branch:
            sha = get_branch_id(node_settings, branch)
        else:
            branch, sha = get_default_branch_and_sha(node_settings)

    branch = branch or get_default_branch(node_settings)

    return branch, sha
