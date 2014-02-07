from nodefilecollector import NodeFileCollector

### Rubeus defined Constants
FOLDER = 'folder'
LEAF = 'item'


DEFAULT_PERMISSIONS = { #Update me to 
    'view': True,
    'edit': False
}
        #'view': node.can_view(user),
        #'edit': node.can_edit(user) and not node.is_registration,

def DEFUALT_URLS(node_api, short_name):
    return {
        'fetch' :'{node_api}{addonshort}/hgrid/'.format(node_api=node_api, addonshort=short_name),
        'upload': '{node_api}{addonshort}/upload/'.format(node_api=node_api, addonshort=short_name)
    }

def to_hgrid(node, auth, mode, **data):
    return NodeFileCollector(node, auth, **data)(mode)

def build_dummy_folder(node_settings, name, permissions=DEFAULT_PERMISSIONS, urls=None, extra=None, **kwargs):
    name = node_settings.config.full_name + ': ' + name if name else node_settings.full_name
    if hasattr(node_settings.config, 'urls') and node_settings.config.urls:
        urls = node_settings.config.urls
    if not urls:
        urls = DEFUALT_URLS(node_settings.owner.api_url, node_settings.config.short_name)
    rv = {
        'addon': node_settings.config.short_name,
        'name': name,
        'iconUrl': node_settings.config.icon_url,
        'kind': FOLDER,
        'extra': extra,
        'isAddonRoot': True,
        'permissions': permissions,
        'accept': {
            'maxSize': node_settings.config.max_file_size,
            'extensions': node_settings.config.accept_extensions
        },
        'urls': urls
    }
    rv.update(kwargs)
    return rv