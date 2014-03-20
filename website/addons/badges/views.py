import httplib as http

from framework.exceptions import HTTPError
from framework.flask import request

from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon, must_not_be_registration,
    must_be_valid_project,
    must_have_permission
)

from framework.auth.decorators import must_be_logged_in

from util import load_badge, build_badge
from model import Badge


@must_be_contributor_or_public
@must_have_addon('badges', 'node')
def badges_widget(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    badges = node.get_addon('badges')
    ret = {
        'complete': True,

    }
    ret.update(badges.config.to_json())
    return ret


@must_be_contributor_or_public
@must_have_addon('badges', 'node')
def award_badge(*args, **kwargs):
    auth = kwargs.get('auth', None)
    badgeid = kwargs.get('badgeid', None)
    badge_bag = kwargs['node_addon']
    if not auth:
        raise HTTPError(http.BAD_REQUEST)
    awarder = auth.user.get_addon('badges')
    if not awarder or not awarder.can_issue:
        raise HTTPError(http.FORBIDDEN)
    badge = load_badge(badgeid)
    return badge_bag.add_badge(badge)


def get_badge(*args, **kwargs):
    _id = kwargs.get('bid', None)
    if _id:
        guid = Badge.load(_id)
        badge = guid.referent
        return badge.to_json()
    raise HTTPError(http.BAD_REQUEST)


@must_be_logged_in
@must_have_addon('badges', 'user')
def new_badge(*args, **kwargs):
    auth = kwargs.get('auth', None)
    badge_data = request.json
    if not auth or not badge_data:
        raise HTTPError(http.BAD_REQUEST)
    awarder = auth.user.get_addon('badges')
    if not awarder or not awarder.can_issue:
        raise HTTPError(http.FORBIDDEN)

    id = build_badge(awarder, badge_data)
    awarder.add_badge(id)
    return 200
