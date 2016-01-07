import io
import os
import errno
import urllib2
from PIL import Image
from collections import defaultdict

from website.addons.badges.settings import *  # noqa


#TODO: Possible security errors
#TODO: Send to task queue may lock up thread
def acquire_badge_image(imageurl, uid):

    location = os.path.join(BADGES_ABS_LOCATION, uid + '.png')

    try:
        os.makedirs(BADGES_ABS_LOCATION)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    try:
        dl = urllib2.urlopen(imageurl)
    except urllib2.URLError:
        return None

    length = int(dl.info().getheaders('Content-Length')[0])
    mime = dl.info().getheaders('Content-Type')[0]

    if length > MAX_IMAGE_SIZE or 'image' not in mime:
        return None

    Image.open(io.BytesIO(dl.read())).save(location)

    return os.path.join(BADGES_LOCATION, uid + '.png')


def sort_badges(items):
    ret = []
    for item in items:
        index = next((ind for ind in ret if ind.badge is item.badge), None)
        if index:
            index.dates[item.awarder.owner.fullname].append((item.issued_date, item.evidence, item.awarder))
            index.amount += 1
        else:
            item.dates = defaultdict(list)
            item.dates[item.awarder.owner.fullname] = [(item.issued_date, item.evidence, item.awarder)]
            item.amount = 1
            ret.append(item)
    return ret


def get_node_badges(node):
    return [assertion for assertion in node.badgeassertion__awarded if not assertion.revoked]


def get_sorted_node_badges(node):
    return sort_badges(get_node_badges(node))


#Lol list comprehensions
def get_user_badges(user):
    return [badge for node in user.contributed for badge in get_node_badges(node)]


def get_sorted_user_badges(user):
    return sort_badges(get_user_badges(user))
