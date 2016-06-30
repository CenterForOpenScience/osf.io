# -*- coding: utf-8 -*-

from website.util import rubeus

from ..api import Figshare

def figshare_hgrid_data(node_settings, auth, parent=None, **kwargs):
    node = node_settings.owner
    if node_settings.figshare_type == 'project':
        item = Figshare.from_settings(node_settings.user_settings).project(node_settings, node_settings.figshare_id)
    else:
        item = Figshare.from_settings(node_settings.user_settings).article(node_settings, node_settings.figshare_id)
    if not node_settings.figshare_id or not node_settings.has_auth or not item:
        return
    #TODO Test me
    #Throw error if neither
    node_settings.figshare_title = item.get('title') or item['items'][0]['title']
    node_settings.save()
    return [
        rubeus.build_addon_root(
            node_settings, u'{0}:{1}'.format(node_settings.figshare_title or 'Unnamed {0}'.format(node_settings.figshare_type or ''), node_settings.figshare_id), permissions=auth,
            nodeUrl=node.url, nodeApiUrl=node.api_url,
            extra={
                'status': (item.get('articles') or item['items'])[0]['status'].lower()
            },
            private_key=kwargs.get('view_only', None),
        )
    ]
