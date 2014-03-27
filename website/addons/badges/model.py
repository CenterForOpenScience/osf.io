"""

"""
import calendar
from datetime import datetime

from framework import fields
from framework import GuidStoredObject, StoredObject

from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.settings import DOMAIN


class Badge(GuidStoredObject):

    redirect_mode = 'proxy'

    _id = fields.StringField(primary=True)

    creator = fields.ForeignField('badgesusersettings', backref='creator')

    #Open Badge protocol
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
    def assertions(self):
        return getattr(self, 'badgeassertion__assertion', [])

    @property
    def deep_url(self):
        return '/badge/{}/'.format(self._id)

    @property
    def url(self):
        return '/badge/{}/'.format(self._id)


#TODO verification hosted and signed
class BadgeAssertion(StoredObject):

    _id = fields.StringField()

    #Backrefs
    badge = fields.ForeignField('badge', backref='assertion')
    node = fields.ForeignField('node', backref='awarded')

    #Custom fields
    revoked = fields.BooleanField(default=False)
    reason = fields.StringField()

    #Required
    issued_on = fields.IntegerField()  # TODO Format

    #Optional
    evidence = fields.StringField()
    expires = fields.StringField()

    def __init__(self, badge, node, evidence=None, save=True):
        self.badge = badge
        self.node = node
        self.evidence = evidence
        self.issued_on = calendar.timegm(datetime.utctimetuple(datetime.utcnow()))
        if save:
            self.save()

    def to_json(self):
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


#TODO Better way around this, No longer needed?
class BadgesNodeSettings(AddonNodeSettingsBase):
    pass


class BadgesUserSettings(AddonUserSettingsBase):

    user = fields.ForeignField('user', backref='organization')

    revocation_list = fields.DictionaryField()  # {'id':'12345', 'reason':'is a loser'}

    def to_json(self, user):
        ret = super(BadgesUserSettings, self).to_json(user)
        ret['can_issue'] = self.can_issue
        ret['badges'] = [Badge.load(_id).to_json() for _id in self.badges]
        ret['configured'] = self.configured
        return ret

    def to_openbadge(self):
        ret = {
            'name': self.user.fullname,
            'email': self.user.email,  # TODO ?
        }
        # if self.description:
        #     ret['description'] = self.description,
        # if self.image:
        #     ret['image'] = self.image,
        # if self.url:
        #     ret['url'] = self.url
        # if self.revocation_list:
        #     ret['revocationList'] = self.revocation_list
        return ret

    @property
    def can_award(self):
        return bool(self.badge__creator)

    @property
    def badges(self):
        return getattr(self, 'badge__creator', [])

    def get_badges_json(self):
        return [badge.to_json() for badge in self.badges]

    def get_badges_json_simple(self):
        return [{'value': badge['id'], 'text': badge['name']} for badge in self.badges]
