# -*- coding: utf -*-

from modularodm import fields, Q

from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase

from . import Badge


#TODO Better way around this, No longer needed?
class BadgesNodeSettings(AddonNodeSettingsBase):
    pass


class BadgesUserSettings(AddonUserSettingsBase):

    revocation_list = fields.DictionaryField()  # {'id':'12345', 'reason':'is a loser'}

    @property
    def can_award(self):
        return bool(self.badges) or len(Badge.get_system_badges()) > 0

    @property
    def badges(self):
        return list(Badge.find(Q('creator', 'eq', self._id))) + [badge for badge in Badge.get_system_badges() if badge.creator != self]

    @property
    def issued(self):
        assertions = []
        for badge in self.badges:
            for assertion in badge.assertions:
                if assertion.awarder == self:
                    assertions.append(assertion)
        return assertions

    def get_badges_json(self):
        return [badge.to_json() for badge in self.badges]

    def get_badges_json_simple(self):
        return [{'value': badge._id, 'text': badge.name} for badge in self.badges]

    def to_json(self, user):
        ret = super(BadgesUserSettings, self).to_json(user)
        ret['badges'] = self.get_badges_json()
        return ret

    def to_openbadge(self):
        ret = {
            'name': self.owner.fullname,
            'email': self.owner.username,
        }
        # Place holder for later when orgaizations get worked on
        # if self.description:
        #     ret['description'] = self.description,
        # if self.image:
        #     ret['image'] = self.image,
        # if self.url:
        #     ret['url'] = self.url
        # if self.revocation_list:
        #     ret['revocationList'] = self.revocation_list
        return ret

    def issued_json(self):
        return [assertion.to_json() for assertion in self.issued]
