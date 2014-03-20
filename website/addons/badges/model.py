"""

"""
from framework import fields
from framework import GuidStoredObject

from website.addons.base import AddonNodeSettingsBase, AddonUserSettingsBase


class Badge(GuidStoredObject):
    _id = fields.StringField(primary=True)
    creator = fields.ForeignField('badgesusersettings')

    name = fields.StringField()
    description = fields.StringField()
    image = fields.StringField()
    criteria = fields.StringField()
    issuer_url = fields.StringField()
    #TODO
    alignment = fields.StringField(list=True)
    tags = fields.StringField(list=True)

    def to_json(self):
        ret = {
            'name': self.name,
            'description': self.description,
            'image': self.image,
            'criteria': self.criteria,
            'issuer_url': self.issuer_url,
            'url': '/badges/{0}'.format(self._id),
        }

        if self.alignment:
            ret['alignment'] = self.alignment
        if self.tags:
            ret['tags'] = self.tags

        return ret

    @property
    def deep_url(self):
        return '/badge/{}/'.format(self._id)


class BadgeAssertion(GuidStoredObject):
    _id = fields.StringField(primary=True)

    recipient = fields.StringField()
    badge_url = fields.StringField()  # URL to badge json
    verify = fields.DictionaryField()
    issued_on = fields.StringField()  # TODO Format

    def to_json(self):
        ret = {
        }
        return ret

    @property
    def deep_url(self):
        return '/badge/assertions/{}/'.format(self._id)


class BadgesNodeSettings(AddonNodeSettingsBase):

    badges = fields.StringField(list=True)

    def to_json(self, user):
        ret = super(BadgesNodeSettings, self).to_json(user)
        ret['badges'] = self.badges
        return ret

    def add_badge(self, badge, save=True):
        self.badges.append(badge)
        if save:
            self.badges.save()
        return True


class BadgesUserSettings(AddonUserSettingsBase):

    can_issue = fields.BooleanField()
    badges = fields.StringField(list=True)

    name = fields.StringField()
    site_url = fields.StringField()
    description = fields.StringField()
    contact = fields.StringField()  # TODO Lock to Email only
    revocationList = fields.DictionaryField()  # {'id':'12345', 'reason':'is a loser'}

    def to_json(self, user):
        ret = super(BadgesUserSettings, self).to_json(user)
        ret['badges'] = [Badge.load(_id).to_json() for _id in self.badges]
        return ret

    @property
    def configured(self):
        configed = (
            self.name and self.name.strip(),
            self.site_url and self.site_url.strip(),
            self.description and self.description.strip(),
            self.contact and self.contact.strip(),
        )
        return configed

    def add_badge(self, id, save=True):
        self.badges.append(id)
        if save:
            self.save()
