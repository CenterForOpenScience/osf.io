"""

"""
import json
from datetime import datetime

from framework import fields
from framework import GuidStoredObject

from website.addons.base import AddonNodeSettingsBase, AddonUserSettingsBase
from website.settings import DOMAIN


class Badge(GuidStoredObject):

    redirect_mode = 'proxy'

    _id = fields.StringField(primary=True)
    creator = fields.StringField()
    creator_name = fields.StringField()

    name = fields.StringField()
    description = fields.StringField()
    image = fields.StringField()
    criteria = fields.StringField()
    #TODO
    alignment = fields.DictionaryField(list=True)
    tags = fields.StringField(list=True)

    def to_json(self):
        ret = {
            'id': self._id,
            'name': self.name,
            'description': self.description,
            'image': self.image,
            'criteria': self.criteria,
            'issuer': '{0}badge/organization/{1}/'.format(DOMAIN, self.creator),
            'issuer_id': self.creator,
            'issuer_name': self.creator_name,
            'url': '{0}{1}/'.format(DOMAIN, self._id),
        }
        if self.alignment:
            ret['alignment'] = self.alignment
        if self.tags:
            ret['tags'] = self.tags

        return ret

    def to_openbadge(self):
        ret = {
            'name': self.name,
            'description': self.description,
            'image': self.image,
            'criteria': self.criteria,
            'issuer': '{0}badge/organization/{1}/json/'.format(DOMAIN, self.creator),
            'url': '{0}{1}/json/'.format(DOMAIN, self._id)
        }

        if self.alignment:
            ret['alignment'] = self.alignment
        if self.tags:
            ret['tags'] = self.tags
        return ret

    @property
    def deep_url(self):
        return '/badge/{}/'.format(self._id)

    @property
    def url(self):
        return '/badge/{}/'.format(self._id)


class BadgeAssertion(GuidStoredObject):

    redirect_mode = 'proxy'

    #Automatic
    _id = fields.StringField(primary=True)

    #Required
    recipient = fields.DictionaryField()
    badge_id = fields.StringField()  # URL to badge json
    verify = fields.DictionaryField()
    issued_on = fields.StringField()  # TODO Format

    #Optional
    image = fields.StringField()
    evidence = fields.StringField()
    expires = fields.StringField()

    #Custom fields
    revoked = fields.BooleanField(default=False)
    reason = fields.StringField()

    def to_json(self):
        #Mozilla Required Fields
        ret = {
            'uid': self._id,
            'recipient': self.recipient,
            'badge': self.badge_id,
            'verify': self.verify,
            'issued_on': datetime.fromtimestamp(self.issued_on).strftime('%Y/%m/%d')
        }
        ret.update(Badge.load(self.badge_id).to_json())

        #Optional Fields
        if self.image:
            ret['image'] = self.image
        if self.evidence:
            ret['evidence'] = self.evidence
        if self.expires:
            ret['expires'] = self.expires

        return ret

    def to_openbadge(self):
        ret = {
            'uid': self._id,
            'recipient': self.recipient,
            'badge': '{}{}/json/'.format(DOMAIN, self.badge_id),
            'verify': self.verify,
            'issuedOn': self.issued_on
        }
        if self.image:
            ret['image'] = self.image
        if self.evidence:
            ret['evidence'] = self.evidence
        if self.expires:
            ret['expires'] = self.expires
        return ret

    @property
    def deep_url(self):
        return '/badge/assertions/{}/'.format(self._id)

    @property
    def url(self):
        return '/badge/assertions/{}/'.format(self._id)


class BadgesNodeSettings(AddonNodeSettingsBase):

    assertions = fields.StringField(list=True)

    def to_json(self, user):
        ret = super(BadgesNodeSettings, self).to_json(user)
        ret['assertions'] = self.assertions
        return ret

    def add_badge(self, assertion, save=True):
        self.assertions.append(assertion)
        if save:
            self.save()
        return True

    def get_assertions(self):
        ret = []
        for assertion in self.assertions:
            temp = BadgeAssertion.load(assertion).to_json()
            if not BadgeAssertion.load(assertion).revoked:
                temp.update(Badge.load(temp['badge']).to_json())
                ret.append(temp)
        return ret


class BadgesUserSettings(AddonUserSettingsBase):

    can_issue = fields.BooleanField()
    badges = fields.StringField(list=True)

    name = fields.StringField()
    url = fields.StringField()
    image = fields.StringField()
    description = fields.StringField()
    email = fields.StringField()  # TODO Lock to Email only
    revocation_list = fields.DictionaryField()  # {'id':'12345', 'reason':'is a loser'}

    def to_json(self, user):
        ret = super(BadgesUserSettings, self).to_json(user)
        ret['can_issue'] = self.can_issue
        ret['badges'] = [Badge.load(_id).to_json() for _id in self.badges]
        ret['configured'] = self.configured
        return ret

    def to_openbadge(self):
        if not self.configured:
            return {}
        ret = {
            'name': self.name,
            'email': self.email,
        }
        if self.description:
            ret['description'] = self.description,
        if self.image:
            ret['image'] = self.image,
        if self.url:
            ret['url'] = self.url
        if self.revocation_list:
            ret['revocationList'] = self.revocation_list
        return ret

    @property
    def configured(self):
        return not (self.name is None  or self.url is None)

    def get_badges_json(self):
        return [Badge.load(_id).to_json() for _id in self.badges]

    def get_badges_json_simple(self):
        return [{'value': Badge.load(_id).to_json()['id'], 'text': Badge.load(_id).to_json()['name']} for _id in self.badges]

    def add_badge(self, id, save=True):
        self.badges.append(id)
        if save:
            self.save()
