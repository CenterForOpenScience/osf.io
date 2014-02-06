# -*- coding: utf-8 -*-
import logging
from mako.template import Template

from framework import request
from framework.auth.decorators import Auth

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon

from ..api import GitHub, to_hgrid, ref_to_params
from .util import _get_refs, _check_permissions

logger = logging.getLogger(__name__)

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
        <span class="github-sha text-muted">${sha[:10]}</span>
    % endif
''')

def github_branch_widget(branches, branch, sha):
    """Render branch selection widget for GitHub add-on. Displayed in the
    name field of HGrid file trees.

    """
    rendered = github_branch_template.render(
        branches=[
            each['name']
            for each in branches
        ],
        branch=branch,
        sha=sha,
    )
    return rendered


def github_hgrid_data(node_settings, auth, parent=None, contents=False, *args, **kwargs):

    # Quit if no repo linked
    if not node_settings.user or not node_settings.repo:
        return

    connection = GitHub.from_settings(node_settings.user_settings)

    branch, sha, branches = _get_refs(
        node_settings,
        branch=kwargs.get('branch'),
        sha=kwargs.get('sha'),
        connection=connection,
    )

    if branch is not None:
        ref = ref_to_params(branch, sha)
        can_edit = _check_permissions(
            node_settings, auth, connection, branch, sha
        )
        name_append = github_branch_widget(branches, branch, sha)
    else:

        ref = None
        can_edit = False
        name_append = None
    name_tpl = ('GitHub: <a class="github-repo-link" href="https://github.com/{user}/{repo}/">'
                '{user}/{repo}</a>{widget}').format(user=node_settings.user,
                                                    repo=node_settings.repo,
                                                    widget=name_append)
    rv = {
        'addon': node_settings.config.short_name,
        'name': name_tpl,
        'kind': 'folder',
        'urls': {
            'upload': node_settings.owner.api_url + 'github/file/' + ref,
            'fetch': node_settings.owner.api_url + 'github/hgrid/' + ref,
            'branch': node_settings.owner.api_url + 'github/hgrid/root/',
        },
        'permissions': {
            'view': True,
            'edit': can_edit,
        },
        'accept': {
            'maxSize': node_settings.config.max_file_size,
            'extensions': node_settings.config.accept_extensions,
        }
    }

    return rv


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
    parent = data.pop('parent', 'null')

    return github_hgrid_data(node_settings, auth=auth, parent=parent, contents=False, **data)


def _get_tree(node_settings, sha, connection=None):

    connection = connection or GitHub.from_settings(node_settings.user_settings)
    tree = connection.tree(
        node_settings.user, node_settings.repo, sha, recursive=True,
    )
    if tree:
        return tree['tree']

@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_hgrid_data_contents(*args, **kwargs):
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
    branch, sha, branches = _get_refs(
        node_addon, req_branch, req_sha, connection=connection
    )
    # Get file tree
    contents = connection.contents(
        user=node_addon.user, repo=node_addon.repo, path=path,
        ref=sha or branch,
    )

    can_edit = _check_permissions(node_addon, auth, connection, branch, sha)

    if contents:
        hgrid_tree = to_hgrid(
            contents, node_url=node.url, node_api_url=node.api_url,
            branch=branch, sha=sha, can_edit=can_edit, parent=path,
        )
    else:
        hgrid_tree = []
    return hgrid_tree
