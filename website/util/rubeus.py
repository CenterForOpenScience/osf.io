# -*- coding: utf-8 -*-
"""Contanins Helper functions for generating correctly
formated hgrid list/folders.
"""
import os
import itertools
import hurry

from framework.auth.decorators import Auth

FOLDER = 'folder'
FILE = 'item'
KIND = 'kind'

# TODO Review me.
DEFAULT_PERMISSIONS = {
    'view': True,
    'edit': False
}


def format_filesize(size):
    return hurry.filesize.size(size, system=hurry.filesize.alternative)


def default_urls(node_api, short_name):
    return {
        'fetch': u'{node_api}{addonshort}/hgrid/'.format(node_api=node_api, addonshort=short_name),
        'upload': u'{node_api}{addonshort}/'.format(node_api=node_api, addonshort=short_name),
    }


def to_hgrid(node, auth, **data):
    """Converts a node into a rubeus grid format

    :param node Node: the node to be parsed
    :param auth Auth: the user authorization object
    :returns: rubeus-formatted dict

    """
    return NodeFileCollector(node, auth, **data).to_hgrid()


def build_addon_root(node_settings, name, permissions=DEFAULT_PERMISSIONS,
                     urls=None, extra=None, **kwargs):
    """Builds the root or "dummy" folder for an addon.

    :param node_settings addonNodeSettingsBase: Addon settings
    :param name String: Additional information for the folder title
        eg. Repo name for Github or bucket name for S3
    :param permissions dict or Auth: Dictionary of permissions for the addon's content or Auth for use in node.can_X methods
    :param urls dict: Hgrid related urls
    :param extra String: Html to be appened to the addon folder name
        eg. Branch switcher for github
    :param kwargs dict: Any additional information to add to the root folder
    :return dict: Hgrid formatted dictionary for the addon root folder

    """
    if name:
        name = u'{0}: {1}'.format(node_settings.config.full_name, name)
    else:
        name = node_settings.config.full_name
    if hasattr(node_settings.config, 'urls') and node_settings.config.urls:
        urls = node_settings.config.urls
    if urls is None:
        urls = default_urls(node_settings.owner.api_url, node_settings.config.short_name)
    if isinstance(permissions, Auth):
        auth = permissions
        permissions = {
            'view': node_settings.owner.can_view(auth),
            'edit': node_settings.owner.can_edit(auth) and not node_settings.owner.is_registration
        }
    rv = {
        'addon': node_settings.config.short_name,
        'addonFullname': node_settings.config.full_name,
        'name': name,
        'iconUrl': node_settings.config.icon_url,
        KIND: FOLDER,
        'extra': extra,
        'isAddonRoot': True,
        'permissions': permissions,
        'accept': {
            'maxSize': node_settings.config.max_file_size,
            'acceptedFiles': node_settings.config.accept_extensions
        },
        'urls': urls
    }
    rv.update(kwargs)
    return rv


# TODO finish or remove me....
def build_addon_item():
    pass


# TODO: Is this used anywhere?
def validate_row(item):
    """Returns whether or not the given item has the minimium
    requirements to be rendered in a rubeus grid
    """
    try:
        item['addon']
        item['name']
        item[KIND]
        item['urls']
        return True
    except KeyError:
        return False


class NodeFileCollector(object):

    """A utility class for creating rubeus formatted node data"""

    def __init__(self, node, auth, **kwargs):
        self.node = node
        self.auth = auth
        self.extra = kwargs
        self.can_view = node.can_view(auth)
        self.can_edit = node.can_edit(auth) if self.can_view else False

    def to_hgrid(self):
        """Return the Rubeus.JS representation of the node's file data, including
        addons and components
        """
        root = self._serialize_node(self.node)
        return [root]

    def _collect_components(self, node):
        rv = []
        for child in node.nodes:
            if not child.is_deleted and node.can_view(self.auth):
                rv.append(self._serialize_node(child))
        return rv

    def _serialize_node(self, node):
        """Returns the rubeus representation of a node folder.
        """
        can_edit = node.can_edit(auth=self.auth)
        can_view = node.can_view(auth=self.auth)
        if can_view:
            children = self._collect_addons(node) + self._collect_components(node)
        else:
            children = []
        return {
            'name': u'{0}: {1}'.format(node.project_or_component.capitalize(), node.title)
                if can_view
                else u'Private Component',
            'kind': FOLDER,
            'permissions': {
                'edit': can_edit,
                'view': can_view
            },
            'urls': {
                'upload': os.path.join(node.api_url, 'osffiles') + '/',
                'fetch': None,
            },
            'children': children
        }

    def _collect_addons(self, node):
        rv = []
        for addon in node.get_addons():
            if addon.config.has_hgrid_files:
                temp = addon.config.get_hgrid_data(addon, self.auth, **self.extra)
                rv.extend(temp or [])
        return rv

# TODO: these might belong in addons module
def collect_addon_assets(node):
    """Return a dictionary containing lists of JS and CSS assets for a node's
    addons.

    :rtype: {'tree_js': <list of JS scripts>, 'tree_css': <list of CSS files>}
    """
    return {
        'tree_js': collect_addon_js(node),
        'tree_css': collect_addon_css(node)
    }


def collect_addon_js(node):
    """Collect JavaScript includes for all add-ons implementing HGrid views.

    :return list: List of JavaScript include paths

    """
    # NOTE: must coerce to list so it is JSON-serializable
    return list(itertools.chain.from_iterable(
        addon.config.include_js.get('files', [])
        for addon in node.get_addons())
    )


def collect_addon_css(node):
    """Collect CSS includes for all addons-ons implementing Hgrid views.

    :return list: List of CSS include paths

    """
    return list(itertools.chain.from_iterable(
        addon.config.include_css.get('files', [])
        for addon in node.get_addons())
    )
