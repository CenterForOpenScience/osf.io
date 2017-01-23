# -*- coding: utf-8 -*-
from website.citations.providers import CitationsProvider
from website.addons.zotero.serializer import ZoteroSerializer

class ZoteroCitationsProvider(CitationsProvider):
    serializer = ZoteroSerializer
    provider_name = 'zotero'

    def _folder_to_dict(self, data):
        return dict(
            name=data['data'].get('name'),
            list_id=data['data'].get('key'),
            parent_id=data['data'].get('parentCollection'),
            id=data['data'].get('key'),
        )
