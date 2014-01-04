"""

"""

from mako.template import Template
from website.addons.base import AddonSettingsBase

class AddonFilesSettings(AddonSettingsBase):

    def render_widget(self):
        return Template('''
            <div mod-meta='{
                "tpl": "util/render_file_tree.mako",
                "uri": "${url}files/",
                "view_kwargs": {
                      "dash": true
                },
                "replace": true
            }'></div>
        ''').render(
            url=self.node.api_url,
        )

    def render_tab(self):
        return {
            'href': '{0}files/'.format(self.node.url),
            'text': 'Files',
        }
