# -*- coding: utf-8 -*-
from website.citations.providers import CitationsProvider
from website.addons.mendeley.serializer import MendeleySerializer

class MendeleyCitationsProvider(CitationsProvider):
    serializer = MendeleySerializer
    provider_name = 'mendeley'

    def _folder_to_dict(self, data):
        return dict(
            name=data.name,
            list_id=data.json['id'],
            parent_id=data.json.get('parent_id'),
            id=data.json.get('id'),
        )
