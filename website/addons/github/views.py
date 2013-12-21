"""

"""

import httplib as http

from framework import request
from framework.exceptions import HTTPError

from website import settings
from website.project.decorators import must_be_contributor
from website.project.decorators import must_be_contributor_or_public
from website.project.views.node import _view_project

@must_be_contributor
def github_settings(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    addons = node.addongithubsettings__addons
    if addons:
        github = addons[0]
        github.user = request.json.get('github_user', '')
        github.repo = request.json.get('github_repo', '')
        github.save()
    else:
        raise HTTPError(http.BAD_REQUEST)

@must_be_contributor
def github_disable(**kwargs):

    node = kwargs.get('node') or kwargs.get('project')
    try:
        node.addons_enabled.remove('github')
        node.save()
    except ValueError:
        pass

@must_be_contributor_or_public
def github_page(**kwargs):

    user = kwargs.get('user')
    node = kwargs.get('node') or kwargs.get('project')

    config = settings.ADDONS_AVAILABLE_DICT['github']

    addons = node.addongithubsettings__addons
    if addons:
        github = addons[0]
        rv = {
            'addon_title': 'GitHub',
            'addon_page': github.render_page(),
            'addon_page_js': config.include_js['page'],
            'addon_page_css': config.include_css['page'],

        }
        rv.update(_view_project(node, user))
        return rv
    else:
        raise HTTPError(http.BAD_REQUEST)
