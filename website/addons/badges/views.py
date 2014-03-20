import json
import httplib as http

from framework.exceptions import HTTPError
from framework.flask import request

from website.models import User
from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon, must_not_be_registration,
    must_be_valid_project,
    must_have_permission
)

from framework.auth.decorators import must_be_logged_in

from util import build_badge, build_assertion
from model import Badge, BadgeAssertion


@must_be_contributor_or_public
@must_have_addon('badges', 'node')
def badges_widget(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    badges = node.get_addon('badges')
    auth = kwargs['auth']
    ret = {
        'complete': True,
        'assertions': badges.get_assertions()
    }
    if auth.user:
        badger = auth.user.get_addon('badges')
        if badger:
            ret.update(badger.to_json(auth.user))

    ret.update(badges.config.to_json())
    return ret


@must_be_contributor_or_public
@must_have_addon('badges', 'node')
def award_badge(*args, **kwargs):
    auth = kwargs.get('auth', None)
    badgeid = request.json.get('badgeid', None)
    badge_bag = kwargs['node_addon']
    if not auth:
        raise HTTPError(http.BAD_REQUEST)
    awarder = auth.user.get_addon('badges')
    if not awarder or not awarder.can_issue:
        raise HTTPError(http.FORBIDDEN)
    badge = Badge.load(badgeid)
    return badge_bag.add_badge(build_assertion(awarder, badge, badge_bag.owner))


def get_assertion(*args, **kwargs):
    _id = kwargs.get('aid', None)
    if _id:
        assertion = BadgeAssertion.load(_id)
        return assertion.to_json()
    raise HTTPError(http.BAD_REQUEST)


def get_assertion_json(*args, **kwargs):
    _id = kwargs.get('aid', None)
    if _id:
        assertion = BadgeAssertion.load(_id)
        return assertion.to_openbadge()
    raise HTTPError(http.BAD_REQUEST)


@must_be_logged_in
@must_have_addon('badges', 'user')
def create_badge(*args, **kwargs):
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


def get_badge(*args, **kwargs):
    _id = kwargs.get('bid', None)
    if _id:
        badge = Badge.load(_id)
        return badge.to_json()
    raise HTTPError(http.BAD_REQUEST)


def get_badge_json(*args, **kwargs):
    _id = kwargs.get('bid', None)
    if _id:
        badge = Badge.load(_id)
        return badge.to_openbadge()
    raise HTTPError(http.BAD_REQUEST)


def get_revoked(*args, **kwargs):
    uid = kwargs.get('uid', None)
    if uid:
        user = '' #TODO load user
        badger = user.get_addon('badges')
        return json.dumps(badger.revocation_list)
    raise HTTPError(http.BAD_REQUEST)


@must_be_logged_in
@must_have_addon('badges', 'user')
def create_organization(*args, **kwargs):
    auth = kwargs.get('auth', None)
    if not auth:
        raise HTTPError(http.BAD_REQUEST)
    settings = auth.user.get_addon('badges')
    if not settings or not settings.can_issue:
        raise HTTPError(http.FORBIDDEN)

    settings.name = request.json['name']
    settings.email = request.json['email']
    settings.description = request.json.get('description', '')
    settings.url = request.json.get('url', '')
    settings.image = request.json.get('image', '')
    settings.save()
    return 200


def get_organization(*args, **kwargs):
    uid = kwargs.get('uid', None)
    if uid:
        user = User.load(uid)
        if user:
            badger = user.get_addon('badges')
            if badger:
                return badger.to_json(user)
    raise HTTPError(http.BAD_REQUEST)


def get_organization_json(*args, **kwargs):
    uid = kwargs.get('uid', None)
    if uid:
        user = User.load(uid)
        if user:
            badger = user.get_addon('badges')
            if badger:
                return badger.to_openbadge()
    raise HTTPError(http.BAD_REQUEST)
