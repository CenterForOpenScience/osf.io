# -*- coding: utf-8 -*-
import os
import logging
import httplib as http

from mako.template import Template
from flask import request

from framework.exceptions import HTTPError

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon
from website.util import rubeus

from website.addons.github.exceptions import ApiError
from website.addons.github.api import GitHub, build_github_urls, ref_to_params
from website.addons.github.utils import get_refs, check_permissions
from website.addons.github.exceptions import NotFoundError


logger = logging.getLogger(__name__)

logging.getLogger('github3').setLevel(logging.WARNING)
logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)

# TODO: Probably should just take a node object instead of having to pass
# in both url and api_url
def to_hgrid(data, node_url, node_api_url=None, branch=None, sha=None,
             can_edit=True, parent=None, **kwargs):
    """
    :param list data: The return value of Github's `contents` endpoint.
    """
    grid = []
    folders = {}

    for datum in data:
        if data[datum].type in ['file', 'blob']:
            item = {
                rubeus.KIND: rubeus.FILE,
                'urls': build_github_urls(
                    data[datum], node_url, node_api_url, branch, sha
                )
            }
        elif data[datum].type in ['tree', 'dir']:
            item = {
                rubeus.KIND: rubeus.FOLDER,
                'children': [],
            }
        else:
            continue

        item.update({
            'addon': 'github',
            'permissions': {
                'view': True,
                'edit': can_edit,
            },
            'urls': build_github_urls(
                data[datum], node_url, node_api_url, branch, sha
            ),
            'accept': {
                'maxSize': kwargs.get('max_size', 128),
                'acceptedFiles': kwargs.get('accepted_files', None)
            }
        })

        head, item['name'] = os.path.split(data[datum].path)
        if parent:
            head = head.split(parent)[-1]
        if head:
            folders[head]['children'].append(item)
        else:
            grid.append(item)

        # Update cursor
        if item[rubeus.KIND] == rubeus.FOLDER:
            key = data[datum].path
            if parent:
                key = key.split(parent)[-1]
            folders[key] = item

    return grid


github_branch_template = Template('''
    % if len(branches) > 1:
            <select class="github-branch-select">
                % for each in branches:
                    <option value="${each}" ${"selected" if each == branch else ""}>${each}</option>
                % endfor
            </select>
    % else:
        <span>${branch}</span>
    % endif
    % if sha:
        <a href="https://github.com/${owner}/${repo}/commit/${sha}" target="_blank" class="github-sha text-muted">${sha[:10]}</a>
    % endif
''')


def github_branch_widget(branches, owner, repo, branch, sha):
    """Render branch selection widget for GitHub add-on. Displayed in the
    name field of HGrid file trees.

    """
    rendered = github_branch_template.render(
        branches=[each.name for each in branches],
        branch=branch,
        sha=sha,
        owner=owner,
        repo=repo
    )
    return rendered


def github_repo_url(owner, repo, branch):
    url = "https://github.com/{0}/{1}/tree/{2}".format(owner, repo, branch)
    return url


def github_hgrid_data(node_settings, auth, **kwargs):

    # Quit if no repo linked
    if not node_settings.complete:
        return

    connection = GitHub.from_settings(node_settings.user_settings)

    # Initialize repo here in the event that it is set in the privacy check
    # below. This potentially saves an API call in _check_permissions, below.
    repo = None

    # Quit if privacy mismatch and not contributor
    node = node_settings.owner
    if node.is_public and not node.is_contributor(auth.user):
        try:
            repo = connection.repo(node_settings.user, node_settings.repo)
        except NotFoundError:
            # TODO: Test me @jmcarp
            # TODO: Add warning message
            logger.error('Could not access GitHub repo')
            return None
        if repo.private:
            return None

    try:
        branch, sha, branches = get_refs(
            node_settings,
            branch=kwargs.get('branch'),
            sha=kwargs.get('sha'),
            connection=connection,
        )
    except NotFoundError:
        # TODO: Show an alert or change GitHub configuration?
        logger.error('GitHub repo not found')
        return

    if branch is not None:
        ref = ref_to_params(branch, sha)
        can_edit = check_permissions(
            node_settings, auth, connection, branch, sha, repo=repo,
        )
        name_append = github_branch_widget(branches, owner=node_settings.user,
            repo=node_settings.repo, branch=branch, sha=sha)
    else:

        ref = None
        can_edit = False
        name_append = None

    name_tpl = '{user}/{repo}'.format(
        user=node_settings.user, repo=node_settings.repo
    )

    permissions = {
        'edit': can_edit,
        'view': True
    }
    urls = {
        'upload': node_settings.owner.api_url + 'github/file/' + (ref or ''),
        'fetch': node_settings.owner.api_url + 'github/hgrid/' + (ref or ''),
        'branch': node_settings.owner.api_url + 'github/hgrid/root/',
        'zip': node_settings.owner.api_url + 'github/zipball/' + (ref or ''),
        'repo': github_repo_url(owner=node_settings.user, repo=node_settings.repo, branch=branch)
    }
    buttons = [
        rubeus.build_addon_button('<i class="icon-download-alt"></i>', 'githubDownloadZip', "Download Zip"),
        rubeus.build_addon_button('<i class="icon-external-link"></i>', 'githubVisitRepo', "Visit Repository"),
    ]

    return [rubeus.build_addon_root(
        node_settings,
        name_tpl,
        urls=urls,
        permissions=permissions,
        extra=name_append,
        branches=[each.name for each in branches],
        buttons=buttons,
    )]


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_root_folder_public(*args, **kwargs):
    """View function returning the root container for a GitHub repo. In
    contrast to other add-ons, this is exposed via the API for GitHub to
    accommodate switching between branches and commits.

    """
    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    data = request.args.to_dict()

    return github_hgrid_data(node_settings, auth=auth, **data)


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_hgrid_data_contents(**kwargs):
    """Return a repo's file tree as a dict formatted for HGrid.

    """
    auth = kwargs['auth']
    node = kwargs['node'] or kwargs['project']
    node_addon = kwargs['node_addon']
    path = kwargs.get('path', '')

    connection = GitHub.from_settings(node_addon.user_settings)
    # The requested branch and sha
    req_branch, req_sha = request.args.get('branch'), request.args.get('sha')
    # The actual branch and sha to use, given the addon settings
    branch, sha, branches = get_refs(
        node_addon, req_branch, req_sha, connection=connection
    )
    # Get file tree
    try:
        contents = connection.contents(
            user=node_addon.user, repo=node_addon.repo, path=path,
            ref=sha or branch,
        )
    except ApiError:
        raise HTTPError(http.NOT_FOUND)

    can_edit = check_permissions(node_addon, auth, connection, branch, sha)

    if contents:
        hgrid_tree = to_hgrid(
            contents, node_url=node.url, node_api_url=node.api_url,
            branch=branch, sha=sha, can_edit=can_edit, parent=path,
            max_size=node_addon.config.max_file_size,
            accepted_files=node_addon.config.accept_extensions
        )
    else:
        hgrid_tree = []
    return hgrid_tree
