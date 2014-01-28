"""

"""

from framework import fields
from website.addons.base import AddonNodeSettingsBase


class AddonLinkNodeSettings(AddonNodeSettingsBase):

    link_url = fields.StringField()

    def to_json(self, user):
        rv = super(AddonLinkNodeSettings, self).to_json(user)
        rv.update({
            'link_url': self.link_url or '',
        })
        return rv
