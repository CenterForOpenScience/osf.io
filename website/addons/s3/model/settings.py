'''
Created on Jan 7, 2014

@author: seto
'''
"""

"""

import json

from framework import fields

from website.addons.base import AddonSettingsBase

class AddonS3Settings(AddonSettingsBase):

    access_key = fields.StringField()
    secret_key = fields.StringField()

    @property
    def embed_url(self):
        return 'http://google.com'

    def render_widget(self):
        if self.access_key and self.secret_key:
            return '''
                <h3>S3 Add-On</h3>
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
            'access_key': self.access_key,
            'secret_key': self.secret_key,
        })
