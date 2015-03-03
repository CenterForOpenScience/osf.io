# -*- coding: utf-8 -*-

import httplib as http
from flask import request

from framework.exceptions import HTTPError

from website.util.sanitize import escape_html
from website.project.decorators import (  # noqa
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
    badgeid = request.json.get('badgeid')
    evidence = request.json.get('evidence')
    node = kwargs['node'] or kwargs['project']
    awarder = kwargs['user_addon']
    if not awarder or not awarder.can_award:
        raise HTTPError(http.FORBIDDEN)
    badge = Badge.load(badgeid)
    if not badge:
        raise HTTPError(http.BAD_REQUEST)
    if badge.is_system_badge:
        return BadgeAssertion.create(badge, node, evidence, awarder=awarder)._id
    return BadgeAssertion.create(badge, node, evidence)._id


@must_have_addon('badges', 'user')
def create_badge(*args, **kwargs):
    badge_data = request.json
    awarder = kwargs['user_addon']

    if (not badge_data or not badge_data.get('badgeName') or
            not badge_data.get('description') or
            not badge_data.get('imageurl') or
            not badge_data.get('criteria')):

        raise HTTPError(http.BAD_REQUEST)
    try:
        id = Badge.create(awarder, escape_html(badge_data))._id
        return {'badgeid': id}, http.CREATED
    except IOError:
        raise HTTPError(http.BAD_REQUEST)


@must_be_valid_project
@must_have_addon('badges', 'user')
@must_have_addon('badges', 'node')
def revoke_badge(*args, **kwargs):
    _id = request.json.get('id')
    reason = request.json.get('reason', '')
    if _id and kwargs['user_addon'].can_award:
        assertion = BadgeAssertion.load(_id)
        if assertion:
            if assertion.badge and assertion.awarder.owner._id == kwargs['user_addon'].owner._id:
                assertion.revoked = True
                assertion.reason = reason
                kwargs['user_addon'].revocation_list[_id] = reason
                assertion.save()
                kwargs['user_addon'].save()
                return http.OK
    raise HTTPError(http.BAD_REQUEST)
