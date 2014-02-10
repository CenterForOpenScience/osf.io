from nodefilecollector import NodeFileCollector
"""Contanins Helper functions for generating correctly
formated hgrid list/folders.
"""
# Rubeus defined Constants
FOLDER = 'folder'
LEAF = 'item'


# TODO Review me.
DEFAULT_PERMISSIONS = {
    'view': True,
    'edit': False
}


def default_urls(node_api, short_name):
    return {
        'fetch': '{node_api}{addonshort}/hgrid/'.format(node_api=node_api, addonshort=short_name),
        'upload': '{node_api}{addonshort}/upload/'.format(node_api=node_api, addonshort=short_name)
    }


def to_hgrid(node, auth, mode, **data):
    """Converts a node into a rubeus grid format

    :param node Node: the node to be parsed
    :param auth Auth: the user authorization to be unused
    :param mode String: page, widget, other
    :return dict: rebeus formatted dict

    """
    return NodeFileCollector(node, auth, **data)(mode)


def build_dummy_folder(node_settings, name, permissions=DEFAULT_PERMISSIONS, urls=None, extra=None, **kwargs):
    """Builds the root or "dummy" folder for an addon.

    :param node_settings addonNodeSettingsBase: Addon settings
    :param name String: Additional information for the folder title
        eg. Repo name for Github or bucket name for S3
    :param permissions dict: Dictionary of permissions for the addon's content
    :param urls dict: Hgrid related urls
    :param extra String: Html to be appened to the addon folder name
        eg. Branch switcher for github
    :param kwargs dict: Any additional information to add to the root folder
    :return dict: Hgrid formatted dictionary for the addon root folder

    """
    name = node_settings.config.full_name + ': ' + \
        name if name else node_settings.full_name
    if hasattr(node_settings.config, 'urls') and node_settings.config.urls:
        urls = node_settings.config.urls
    if urls is None:
        urls = default_urls(node_settings.owner.api_url, node_settings.config.short_name)
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


def validate_row(item):
    """Returns whether or not the given item has the minimium
    requirements to be rendered in a rubeus grid
    """
    try:
        item['addon']
        item['name']
        item['kind']
        item['urls']
        return True
    except AttributeError:
        return False
