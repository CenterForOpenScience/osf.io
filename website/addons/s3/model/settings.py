'''
Created on Jan 7, 2014

@author: seto
'''
"""

"""

import json

from framework import fields

from website.addons.base import AddonSettingsBase

class AddonS3UserSettings(AddonUserSettingsBase):

    access_key = fields.StringField()
    secret_key = fields.StringField()



class AddonS3NodeSettings(AddonSettingsBase):

    bucket = fields.StringField()

    user_settings = fields.ForeignField(
        'addons3usersettings', backref='authorized'
    )

    registration_data = fields.DictionaryField()

    def to_json(self, user):
        s3_user = user.get_addon('s3')
        rv = {
            'bucket': self.bucket
        }
        settings = self.user_settings
        if settings:
            rv.update({
                'access_key': settings.access_key,
                'secret_key': settings.secret_key
            })
        return rv

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



    def render_page(self):
        if self.secret_key:
            return '''
                <h3>Amazon S3 Page</h3>
                <div>{xml}</div>
            '''
            
        return '''
            <div>
                Zotero page not configured:
                Configure this addon on the <a href="/{nid}/settings/">settings</a> page,
                or click <a class="widget-disable" href="{url}settings/zotero/disable/">here</a> to disable it.
            </div>
        '''
    
    def render_tab(self):
        return {
            'href': '{0}zotero/'.format(self.node.url),
            'text': 'Amazon S3',
        }
