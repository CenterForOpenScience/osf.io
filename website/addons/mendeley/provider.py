# -*- coding: utf-8 -*-
from website.addons.citations.provider import CitationsProvider
from website.addons.mendeley.serializer import MendeleySerializer

class MendeleyCitationsProvider(CitationsProvider):

    def __init__(self):
        super(MendeleyCitationsProvider, self).__init__('mendeley')

    @property
    def serializer(self):
        return MendeleySerializer

    def widget(self, node_addon):
        ret = super(MendeleyCitationsProvider, self).widget(node_addon)
        ret.update({
            'list_id': node_addon.mendeley_list_id
        })
        return ret

    def _folder_to_dict(self, data):
        return dict(
            name=data.name,
            list_id=data.json['id'],
            parent_id=data.json.get('parent_id'),
            id=data.json.get('id'),
        )

    def _folder_id(self, node_addon):
        return node_addon.mendeley_list_id

    def add_show_more(self, node_addon, contents, list_id, page):
        contents.append({
            'name': 'Show more',
            'kind': 'message',
            'urls': {
                'fetch': node_addon.owner.api_url_for('mendeley_citation_list', zotero_list_id=list_id, page=page)
            }
        })

    def is_first_page(self, page):
        return page is None
