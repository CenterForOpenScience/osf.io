import httplib as http

from website.models import User

from framework.exceptions import HTTPError

from ..model import Badge, BadgeAssertion


def get_assertion_json(*args, **kwargs):
    _id = kwargs.get('aid', None)
    if _id:
        assertion = BadgeAssertion.load(_id)
        if not assertion.revoked:
            return assertion.to_openbadge()
        return {'revoked': True}, http.GONE
    raise HTTPError(http.BAD_REQUEST)


def get_badge_json(*args, **kwargs):
    _id = kwargs.get('bid', None)
    if _id:
        badge = Badge.load(_id)
        return badge.to_openbadge()
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
