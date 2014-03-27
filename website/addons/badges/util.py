import os
import urllib
import calendar
from PIL import Image
from datetime import datetime

from website.util.sanitize import deep_clean

from model import Badge, BadgeAssertion


#TODO Clean with bleach
def build_badge(issuer, badge):
    deep_clean(badge)
    new = Badge()
    new.creator = issuer.owner
    new.name = badge['badgeName']
    new.description = badge['description']
    new.image = badge['imageurl']
    new.criteria = badge['criteria']
    #TODO alignment and tags

    new._ensure_guid()

    new.image = deal_with_image(badge['imageurl'], new._id)
    new.save()
    return new._id


def build_assertion(issuer, badge, node, evidence, verify_method='hosted'):
    assertion = BadgeAssertion()
    assertion.issued_on = calendar.timegm(datetime.utctimetuple(datetime.utcnow()))
    assertion.badge = badge

    #TODO Signed and hosted
    if evidence:
        assertion.evidence = evidence
    assertion.save()
    return assertion._id


#TODO: Possible security errors
#TODO: Send to task queue may lock up thread
def deal_with_image(imageurl, uid):
    from . import BADGES_LOCATION, BADGES_ABS_LOCATION

    location = os.path.join(BADGES_ABS_LOCATION, uid + '.png')

    if not os.path.exists(BADGES_ABS_LOCATION):
        os.makedirs(BADGES_ABS_LOCATION)

    ret, _ = urllib.urlretrieve(imageurl)
    Image.open(ret).save(location)

    return os.path.join(BADGES_LOCATION, uid + '.png')
