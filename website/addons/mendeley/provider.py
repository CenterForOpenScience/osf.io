from website.addons.citations import provider
from .model import MendeleyNodeSettings
from website.addons.citations.utils import serialize_account, serialize_folder, serialize_urls

class MendeleyCitationsProvider(provider.CitationsProvider):

    def __init__(self):
        super(MendeleyCitationsProvider, self).__init__('mendeley')
        
    def widget(self, node_addon):

        ret = super(MendeleyCitationsProvider, self).widget(node_addon)
        ret.update({
            'list_id': node_addon.mendeley_list_id
        })
        return ret

    def _extract_folder(self, data):
        return serialize_folder(
            data.name,
            list_id=data.json['id'],
            parent_id=data.json.get('parent_id'),
            id=data.json.get('id')
        )

    def _serialize_folder(self, folder, node_addon):
        return {
            'data': folder,
            'kind': 'folder',
            'name': folder['name'],
            'id': folder['id'],
            'urls': {
                'fetch': node_addon.owner.api_url_for(
                    'mendeley_citation_list',
                    mendeley_list_id=folder['id']),
            },
        }

    def _folder_id(self, node_addon):

        return node_addon.mendeley_list_id
