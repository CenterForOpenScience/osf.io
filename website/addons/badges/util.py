import urllib
import calendar
from datetime import datetime

from website.settings import DOMAIN

from model import Badge, BadgeAssertion


def is_valid_badge(badge):
    pass


#TODO Clean with bleach
def build_badge(issuer, badge):
    new = Badge()
    new.creator = issuer.owner._id
    new.creator_name = issuer.name
    new.name = badge['badgeName']
    new.description = badge['description']
    new.image = badge['imageurl']
    new.criteria = badge['criteria']
    #TODO alignment and tags
    new.save()
    return new._id


def build_assertion(issuer, badge, node, evidence, verify_method='hosted'):
    assertion = BadgeAssertion()
    assertion.issued_on = calendar.timegm(datetime.utctimetuple(datetime.utcnow()))  # Todo make an int field?
    assertion.badge_id = badge._id
    assertion.recipient = {
        'type': 'osfProject',
        'identity': node._id,  # Change to node url
        'hashed': False,
    }
    assertion._ensure_guid()
    #TODO Signed and hosted
    assertion.verify = {
        'type': 'hosted',
        'url': '{}{}/'.format(DOMAIN, assertion._id)  # is so meta even this acronym
    }
    if evidence:
        assertion.evidence = evidence
    assertion.save()
    return assertion._id


def build_issuer(name, url, extra={}):
    issuer = {
        'name': name,
        'url': url,
    }
    issuer.update(extra)
    return issuer
