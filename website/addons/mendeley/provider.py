from website.addons.citations.provider import CitationsProvider
from website.addons.citations.utils import serialize_folder

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

    def _extract_folder(self, data):
        return serialize_folder(
            data.name,
            list_id=data.json['id'],
            parent_id=data.json.get('parent_id'),
            id=data.json.get('id')
        )

    def _folder_id(self, node_addon):

        return node_addon.mendeley_list_id
