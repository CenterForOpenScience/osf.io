"""

"""

import json

from framework import fields

from website.addons.base import AddonSettingsBase

class AddonFigShareSettings(AddonSettingsBase):

    figshare_id = fields.StringField()

    @property
    def embed_url(self):
        return 'http://wl.figshare.com/articles/{fid}/embed?show_title=1'.format(
            fid=self.figshare_id,
        )

    def render_widget(self):
        if self.figshare_id:
            return '''
                <h3>FigShare Add-On</h3>
                <iframe
                    src="{embed}"
                    width="{width}"
                    height="{height}"
                    frameborder="0"
                ></iframe>
            '''.format(
                embed=self.embed_url,
                width=9999,
                height=300,
            )

    def meta_json(self):
        return json.dumps({
            'figshare_id': self.figshare_id,
        })
