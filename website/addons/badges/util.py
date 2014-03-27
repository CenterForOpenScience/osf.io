import os
import urllib
from PIL import Image


from website.util.sanitize import deep_clean

from model import Badge


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


def get_node_badges(node):
    assertions = getattr(node, 'badgeassertion__awarded', [])
    if assertions:
        assertions = [assertion for assertion in assertions if not assertion.revoked]
    return assertions
