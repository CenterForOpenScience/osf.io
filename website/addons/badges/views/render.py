import httplib as http

from framework.exceptions import HTTPError

from website.project.views.node import _view_project
from website.project.decorators import (  # noqa
    must_be_contributor_or_public,
    must_have_addon, must_not_be_registration,
    must_be_valid_project,
    must_have_permission,
)

from ..model import Badge
from ..util import get_node_badges, get_sorted_node_badges


@must_be_contributor_or_public
@must_have_addon('badges', 'node')
def badges_widget(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    ret = {
        'complete': True,
        'assertions': get_node_badges(node)
    }
    if auth.user:
        badger = auth.user.get_addon('badges')
        if badger:
            ret.update(badger.to_json(auth.user))
            ret['uid'] = auth.user._id

    ret.update(kwargs['node_addon'].config.to_json())
    return ret


@must_be_contributor_or_public
@must_have_addon('badges', 'node')
def badges_page(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']
    ret = {
        'complete': True,
        'assertions': get_sorted_node_badges(node),
    }
    if auth.user:
        badger = auth.user.get_addon('badges')
        if badger:
            ret.update(badger.to_json(auth.user))
            ret['uid'] = auth.user._id
    ret.update(_view_project(node, auth))
    return ret


@must_have_addon('badges', 'user')
def organization_badges_listing(*args, **kwargs):
    return kwargs['user_addon'].get_badges_json_simple()


def view_badge(*args, **kwargs):
    badge = Badge.load(kwargs.get('bid', None))
    if badge:
        return {
            'badge': badge,
            'assertions': badge.assertions,
        }
    raise HTTPError(http.NOT_FOUND)


@must_have_addon('badges', 'user')
def dashboard_badges(*args, **kwargs):
    return {'badges': kwargs['user_addon'].badges}


@must_have_addon('badges', 'user')
def dashboard_assertions(*args, **kwargs):
    return {'assertions': kwargs['user_addon'].issued}
