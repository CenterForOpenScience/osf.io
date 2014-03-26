import httplib as http

from framework.exceptions import HTTPError
from framework.flask import request

from website.models import User, Node
from website.util.sanitize import deep_clean
from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon, must_not_be_registration,
    must_be_valid_project,
    must_have_permission
)
from website.project.views.node import _view_project

from framework.auth.decorators import must_be_logged_in

from util import build_badge, build_assertion
from model import Badge, BadgeAssertion


@must_be_logged_in
def get_user_badges(*args, **kwargs):
    auth = kwargs['auth']
    if auth and auth.user._id == kwargs['uid']:
        return auth.user.get_addon('badges').get_badges_json_simple()
    else:
        raise HTTPError(http.FORBIDDEN)


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
            ret['uid'] = auth.user._id

    ret.update(badges.config.to_json())
    return ret


@must_be_valid_project
@must_be_contributor_or_public
@must_have_addon('badges', 'node')
def badges_page(*args, **kwargs):
    node = kwargs['node'] or kwargs['project']
    badges = node.get_addon('badges')
    auth = kwargs['auth']

    ret = {
        'complete': True,
        'assertions': badges.get_assertions(),
    }
    if auth.user:
        badger = auth.user.get_addon('badges')
        if badger:
            ret.update(badger.to_json(auth.user))
            ret['uid'] = auth.user._id
    ret.update(_view_project(node, kwargs['auth']))

    return ret


@must_be_contributor_or_public
@must_have_addon('badges', 'node')
@must_have_addon('badges', 'user')
def award_badge(*args, **kwargs):
    auth = kwargs.get('auth', None)
    badgeid = request.json.get('badgeid', None)
    evidence = request.json.get('evidence', None)
    badge_bag = kwargs['node_addon']
    if not auth:
        raise HTTPError(http.BAD_REQUEST)
    awarder = auth.user.get_addon('badges')
    if not awarder or not awarder.can_issue:
        raise HTTPError(http.FORBIDDEN)
    badge = Badge.load(badgeid)
    if not badge or not awarder.can_award:
        raise HTTPError(http.BAD_REQUEST)
    return badge_bag.add_badge(build_assertion(awarder, badge, badge_bag.owner, evidence))


def get_assertion(*args, **kwargs):
    _id = kwargs.get('aid', None)
    if _id:
        assertion = BadgeAssertion.load(_id)
        if not assertion.revoked:
            data = assertion.to_json()
            data['batter'] = assertion.to_openbadge()
            data['project_name'] = Node.load(data['recipient']['identity']).title
            data['contributors'] = Node.load(data['recipient']['identity']).contributors
            return data
        return {'revoked': True}, 410
    raise HTTPError(http.BAD_REQUEST)


def get_assertion_json(*args, **kwargs):
    _id = kwargs.get('aid', None)
    if _id:
        assertion = BadgeAssertion.load(_id)
        if not assertion.revoked:
            return assertion.to_openbadge()
        return {'revoked': True}, 410
    raise HTTPError(http.BAD_REQUEST)


@must_be_logged_in
@must_have_addon('badges', 'user')
def create_badge(*args, **kwargs):
    auth = kwargs.get('auth', None)
    badge_data = request.json
    if not auth or not badge_data:
        raise HTTPError(http.BAD_REQUEST)
    if not badge_data.get('badgeName', None) or not badge_data.get('description', None) or not badge_data.get('imageurl', None) or not badge_data.get('criteria', None):
        raise HTTPError(http.BAD_REQUEST)
    awarder = auth.user.get_addon('badges')
    if not awarder or not awarder.can_issue:
        raise HTTPError(http.FORBIDDEN)

    id = build_badge(awarder, badge_data)
    awarder.add_badge(id)
    return {'badgeid': id}, 200


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


@must_be_logged_in
@must_be_valid_project
@must_have_addon('badges', 'user')
@must_have_addon('badges', 'node')
def revoke_badge(*args, **kwargs):
    uid = kwargs['auth'].user._id
    _id = request.json.get('id', None)
    reason = request.json.get('reason', None)
    if _id and reason:
        assertion = BadgeAssertion.load(_id)
        if assertion:
            badge = Badge.load(assertion.badge_id)
            if badge and badge.creator == uid:
                assertion.revoked = True
                assertion.reason = reason
                User.load(uid).get_addon('badges').revocation_list[_id] = reason
                assertion.save()
                User.load(uid).get_addon('badges').save()
                return 200
    raise HTTPError(http.BAD_REQUEST)


def get_revoked_json(*args, **kwargs):
    uid = kwargs.get('uid', None)
    if uid:
        user = User.load(uid)  # TODO load user
        badger = user.get_addon('badges')
        return badger.revocation_list
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
    if not request.json.get('name') or request.json.get('email'):
        raise HTTPError(http.BAD_REQUEST)
    deep_clean(request.json)
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

