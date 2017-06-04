# -*- coding: utf-8 -*-

import calendar
from bson import ObjectId
from datetime import datetime

from modularodm import fields, Q

from framework.mongo import StoredObject
from framework.guid.model import GuidStoredObject

from website.settings import DOMAIN
from website.util import web_url_for, api_url_for
from website.addons.badges.util import acquire_badge_image


class Badge(GuidStoredObject):

    _id = fields.StringField(primary=True)

    creator = fields.ForeignField('badgesusersettings')

    is_system_badge = fields.BooleanField(default=False)

    #Open Badge protocol
    name = fields.StringField()
    description = fields.StringField()
    image = fields.StringField()
    criteria = fields.StringField()

    #TODO implement tags and alignment
    alignment = fields.DictionaryField(list=True)
    tags = fields.StringField(list=True)

    @classmethod
    def get_system_badges(cls):
        return cls.find(Q('is_system_badge', 'eq', True))

    @classmethod
    def create(cls, user_settings, badge_data, save=True):
        badge = cls()
        badge.creator = user_settings
        badge.name = badge_data['badgeName']
        badge.description = badge_data['description']
        badge.criteria = badge_data['criteria']
        badge._ensure_guid()
        badge.image = acquire_badge_image(badge_data['imageurl'], badge._id)
        if not badge.image:
            raise IOError
        if save:
            badge.save()
        return badge

    @property
    def description_short(self):
        words = self.description.split(' ')
        if len(words) < 9:
            return ' '.join(words)
        return '{}...'.format(' '.join(words[:9]))

    #TODO Auto link urls?
    @property
    def criteria_list(self):
        tpl = '<ul>{}</ul>'
        stpl = '<li>{}</li>'
        lines = self.criteria.split('\n')
        return tpl.format(' '.join([stpl.format(line) for line in lines if line]))  # Please dont kill me Steve

    @property
    def assertions(self):
        return BadgeAssertion.find(Q('badge', 'eq', self._id))

    @property
    def awarded_count(self):
        return len(self.assertions)

    @property
    def unique_awards_count(self):
        return len({assertion.node._id for assertion in self.assertions})

    @property
    def deep_url(self):
        return web_url_for('view_badge', bid=self._id)

    @property
    def url(self):
        return web_url_for('view_badge', bid=self._id)

    def make_system_badge(self, save=True):
        self.is_system_badge = True
        self.save()

    def to_json(self):
        return {
            'id': self._id,
            'name': self.name,
            'description': self.description,
            'image': self.image,
            'criteria': self.criteria,
            'alignment': self.alignment,
            'tags': self.tags,
        }

    def to_openbadge(self):
        return {
            'name': self.name,
            'description': self.description,
            'image': self.image,
            'criteria': self.criteria,
            'issuer': api_url_for('get_organization_json', _absolute=True, uid=self.creator.owner._id),
            'url': '{0}{1}/json/'.format(DOMAIN, self._id),  # web url for and GUIDs?
            'alignment': self.alignment,
            'tags': self.tags,
        }


#TODO verification hosted and signed
class BadgeAssertion(StoredObject):

    _id = fields.StringField(default=lambda: str(ObjectId()))

    #Backrefs
    badge = fields.ForeignField('badge')
    node = fields.ForeignField('node')
    _awarder = fields.ForeignField('badgesusersettings')

    #Custom fields
    revoked = fields.BooleanField(default=False)
    reason = fields.StringField()

    #Required
    issued_on = fields.IntegerField(required=True)

    #Optional
    evidence = fields.StringField()
    expires = fields.StringField()

    @classmethod
    def create(cls, badge, node, evidence=None, save=True, awarder=None):
        b = cls()
        b.badge = badge
        b.node = node
        b.evidence = evidence
        b.issued_on = calendar.timegm(datetime.utctimetuple(datetime.utcnow()))
        b._awarder = awarder
        if save:
            b.save()
        return b

    @property
    def issued_date(self):
        return datetime.fromtimestamp(self.issued_on).strftime('%Y/%m/%d')

    @property
    def verify(self, vtype='hosted'):
        return {
            'type': 'hosted',
            'url': api_url_for('get_assertion_json', _absolute=True, aid=self._id)
        }

    @property
    def recipient(self):
        return {
            'idenity': self.node._id,  # TODO: An unknown amount of code may depend on this typo
            'type': 'osfnode',  # TODO Could be an email?
            'hashed': False
        }

    @property
    def awarder(self):
        if self.badge.is_system_badge and self._awarder:
            return self._awarder
        return self.badge.creator

    def to_json(self):
        return {
            'uid': self._id,
            'recipient': self.node._id,
            'badge': self.badge._id,
            'verify': self.verify,
            'issued_on': self.issued_date,
            'evidence': self.evidence,
            'expires': self.expires
        }

    def to_openbadge(self):
        return {
            'uid': self._id,
            'recipient': self.recipient,
            'badge': '{}{}/json/'.format(DOMAIN, self.badge._id),  # GUIDs Web url for
            'verify': self.verify,
            'issuedOn': self.issued_on,
            'evidence': self.evidence,
            'expires': self.expires
        }
