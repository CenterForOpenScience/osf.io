from framework import fields

from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase

from ..util import get_system_badges

#TODO Better way around this, No longer needed?
class BadgesNodeSettings(AddonNodeSettingsBase):
    pass


class BadgesUserSettings(AddonUserSettingsBase):

    revocation_list = fields.DictionaryField()  # {'id':'12345', 'reason':'is a loser'}

    @property
    def can_issue(self):
        return self.owner.is_organization

    @property
    def can_award(self):
        return self.can_issue

    @property
    def badges(self):
        return self.badge__creator

    def get_badges_json(self):
        return [badge.to_json() for badge in self.badges]

    def get_badges_json_simple(self):
        return [{'value': badge._id, 'text': badge.name} for badge in get_system_badges()] +\
        [{'value': badge._id, 'text': badge.name} for badge in self.badges if not badge.is_system_badge]

    def to_json(self, user):
        ret = super(BadgesUserSettings, self).to_json(user)
        ret['can_issue'] = self.can_issue
        ret['badges'] = self.get_badges_json() + [badge.to_json() for badge in get_system_badges() if badge.creator != self]
        return ret

    def to_openbadge(self):
        ret = {
            'name': self.owner.fullname,
            'email': self.owner.email,  # TODO ?
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
