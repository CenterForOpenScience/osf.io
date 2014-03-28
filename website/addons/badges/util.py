import os
import urllib
from PIL import Image


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
    assertions = node.badgeassertion__awarded
    if assertions:
        assertions = [assertion for assertion in assertions if not assertion.revoked]
    return assertions
