from addons.base.apps import BaseAddonAppConfig



class WikiAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.wiki'
    label = 'addons_wiki'

    short_name = 'wiki'
    full_name = 'Wiki'

    owners = ['node']

    added_default = ['node']
    added_mandatory = []

    views = ['widget', 'page']
    configs = []

    categories = ['documentation']

    include_js = {
        'widget': [],
        'page': [],
    }

    include_css = {
        'widget': [],
        'page': [],
    }

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
