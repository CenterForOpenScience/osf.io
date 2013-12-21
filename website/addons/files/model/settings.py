"""

"""

from website.addons.base import AddonSettingsBase

class AddonFilesSettings(AddonSettingsBase):

    def render_widget(self):
        return '''
            <div mod-meta='{{
                "tpl": "util/render_file_tree.mako",
                "uri": "{url}get_files/",
                "view_kwargs": {{
                      "dash": true
                }},
                "replace": true
            }}'></div>
        '''.format(
            url=self.node.api_url,
        )

    def render_tab(self):
        return '''
            <a href="{url}files/">Files</a>
        '''.format(
            url=self.node.url,
        )
