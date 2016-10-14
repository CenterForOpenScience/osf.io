from addons.base.apps import BaseAddonConfig


class WikiAddonConfig(BaseAddonConfig):

    name = 'addons.wiki'
    label = 'addons_wiki'
    full_name = 'Wiki'

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
