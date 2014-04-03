import httplib as http

from framework.flask import request
from framework.exceptions import HTTPError

from website.util.sanitize import deep_clean
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
    badgeid = request.json.get('badgeid', None)
    evidence = request.json.get('evidence', None)
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

    if not badge_data or not badge_data.get('badgeName', None) or \
        not badge_data.get('description', None) or \
        not badge_data.get('imageurl', None) or \
        not badge_data.get('criteria', None):

        raise HTTPError(http.BAD_REQUEST)

    id = Badge.create(awarder, deep_clean(badge_data))._id
    return {'badgeid': id}, 200


@must_be_valid_project
@must_have_addon('badges', 'user')
@must_have_addon('badges', 'node')
def revoke_badge(*args, **kwargs):
    _id = request.json.get('id', None)
    reason = request.json.get('reason', None)
    if _id and reason is not None and kwargs['user_addon'].can_award:
        assertion = BadgeAssertion.load(_id)
        if assertion:
            if assertion.badge and assertion.awarder.owner._id == kwargs['user_addon'].owner._id:
                assertion.revoked = True
                assertion.reason = reason
                kwargs['user_addon'].revocation_list[_id] = reason
                assertion.save()
                kwargs['user_addon'].save()
                return 200
    raise HTTPError(http.BAD_REQUEST)
