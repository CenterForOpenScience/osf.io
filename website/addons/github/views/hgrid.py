from mako.template import Template

from framework import request
from framework.auth import get_current_user

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon

from ..api import GitHub, tree_to_hgrid, ref_to_params
from .util import _get_refs, _check_permissions, MESSAGES

github_branch_template = Template('''
    % if len(branches) > 1:
        <form style="display: inline;">
            <select class="github-branch-select">
                % for each in branches:
                    <option value="${each}" ${"selected" if each == branch else ""}>${each}</option>
                % endfor
            </select>
        </form>
    % else:
        <span>${branch}</span>
    % endif
    % if sha:
        <span class="github-sha">${sha}</span>
    % endif
''')

def github_branch_widget(branches, branch, sha):
    """Render branch selection widget for GitHub add-on. Displayed in the
    name field of HGrid file trees.

    """
    return github_branch_template.render(
        branches=[
            each['name']
            for each in branches
        ],
        branch=branch,
        sha=sha,
    )

def github_dummy_folder(node_settings, auth, link='', parent=None, **kwargs):

    # Quit if no repo linked
    if not node_settings.user or not node_settings.repo:
        return

    connection = GitHub.from_settings(node_settings.user_settings)

    rv = {
        'addonName': 'GitHub',
        'maxFilesize': node_settings.config.max_file_size,
        'uid': 'github:{0}'.format(node_settings._id),
        'name': 'GitHub: {0}/{1}'.format(
            node_settings.user, node_settings.repo,
        ),
        'parent_uid': parent or 'null',
        'type': 'folder',
        'can_view': False,
        'can_edit': False,
        'permission': False,
    }

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

        rv.update({
            'nameExtra': github_branch_widget(branches, branch, sha),
            'can_view': True,
            'can_edit': can_edit,
            'permission': can_edit,
            'uploadUrl': node_settings.owner.api_url + 'github/file/',
            'lazyLoad': node_settings.owner.api_url + 'github/hgrid/',
            'data': {
                'branch': branch,
                'sha': sha,
            },
        })
        if ref:
            rv['uploadUrl'] += '?' + ref

    return rv


@must_be_contributor_or_public
@must_have_addon('github', 'node')
def github_dummy_folder_public(*args, **kwargs):
    """View function returning the dummy container for a GitHub repo. In
    contrast to other add-ons, this is exposed via the API for GitHub to
    accommodate switching between branches and commits.

    """
    node_settings = kwargs['node_addon']
    auth = kwargs['auth']
    data = request.args.to_dict()

    parent = data.pop('parent', 'null')

    return github_dummy_folder(node_settings, auth, parent, **data)


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
    branch, sha, branches = _get_refs(node_addon, req_branch, req_sha,
                                        connection=connection)
    # Get file tree
    contents = connection.contents(
        user=node_addon.user, repo=node_addon.repo, path=path,
        ref=sha or branch,
    )
    parent = request.args.get('parent', 'null')
    can_edit = _check_permissions(node_addon, auth, connection, branch, sha)
    if contents:
        hgrid_tree = tree_to_hgrid(
            contents, user=node_addon.user,
            branch=branch, sha=sha,
            repo=node_addon.repo, node=node, node_settings=node_addon,
            parent=parent,
            can_edit=can_edit,
        )
    else:
        hgrid_tree = []
    return hgrid_tree
