import httplib as http

from framework.flask import request
from framework.exceptions import HTTPError

from website.models import User

from website.util.sanitize import deep_clean

from framework.auth.decorators import must_be_logged_in
from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon, must_not_be_registration,
    must_be_valid_project,
    must_have_permission
)

from ..model import Badge, BadgeAssertion


@must_be_contributor_or_public
@must_have_addon('badges', 'node')
@must_have_addon('badges', 'user')
def award_badge(*args, **kwargs):
    auth = kwargs.get('auth', None)
    badgeid = request.json.get('badgeid', None)
    evidence = request.json.get('evidence', None)
    node = kwargs['node'] or kwargs['project']
    if not auth:
        raise HTTPError(http.BAD_REQUEST)
    awarder = auth.user.get_addon('badges')
    if not awarder or not awarder.can_issue:
        raise HTTPError(http.FORBIDDEN)
    badge = Badge.load(badgeid)
    if not badge or not awarder.can_award:
        raise HTTPError(http.BAD_REQUEST)
    if badge.is_system_badge:
        return BadgeAssertion.create(badge, node, evidence, awarder=awarder)._id
    return BadgeAssertion.create(badge, node, evidence)._id


@must_be_logged_in
@must_have_addon('badges', 'user')
def create_badge(*args, **kwargs):
    auth = kwargs.get('auth', None)

    if not auth or not auth.user.is_organization:
        raise HTTPError(http.FORBIDDEN)

    badge_data = request.json
    awarder = auth.user.get_addon('badges')

    if not badge_data or not badge_data.get('badgeName', None) or \
        not badge_data.get('description', None) or \
        not badge_data.get('imageurl', None) or \
        not badge_data.get('criteria', None):

        raise HTTPError(http.BAD_REQUEST)

    id = Badge.create(awarder, deep_clean(badge_data))._id
    return {'badgeid': id}, 200


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
