import os
import urllib
from PIL import Image
from collections import defaultdict

from modularodm.query.querydialect import DefaultQueryDialect as Q


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


def sort_badges(items):
    ret = []
    for item in items:
        index = [ind for ind in ret if ind.badge is item.badge]
        if index:
            index[0].dates[item.awarder.owner.fullname].append((item.issued_date, item.evidence, item.awarder))
            index[0].amount += 1
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
    return [badge for node in user.node__contributed for badge in get_node_badges(node)]


def get_sorted_user_badges(user):
    return sort_badges(get_user_badges(user))


def get_system_badges():
    from website.addons.badges.model.badges import Badge
    return Badge.find(Q('is_system_badge', 'eq', True))
