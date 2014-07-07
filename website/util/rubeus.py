# -*- coding: utf-8 -*-
"""Contains helper functions for generating correctly
formatted hgrid list/folders.
"""
import os
import hurry

from framework.auth import Auth

FOLDER = 'folder'
FILE = 'item'
KIND = 'kind'

# TODO: Validate the JSON schema, esp. for addons

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

    :param Node node: the node to be parsed
    :param Auth auth: the user authorization object
    :returns: rubeus-formatted dict

    """
    return NodeFileCollector(node, auth, **data).to_hgrid()


def build_addon_root(node_settings, name, permissions=None,
                     urls=None, extra=None, buttons=None, **kwargs):
    """Builds the root or "dummy" folder for an addon.

    :param addonNodeSettingsBase node_settings: Addon settings
    :param String name: Additional information for the folder title
        eg. Repo name for Github or bucket name for S3
    :param dict or Auth permissions: Dictionary of permissions for the addon's content or Auth for use in node.can_X methods
    :param dict urls: Hgrid related urls
    :param String extra: Html to be appened to the addon folder name
        eg. Branch switcher for github
    :param list of dicts buttons: List of buttons to appear in HGrid row. Each
        dict must have 'text', a string that will appear on the button, and
        'action', the name of a function in
    :param dict kwargs: Any additional information to add to the root folder
    :return dict: Hgrid formatted dictionary for the addon root folder

    """
    permissions = permissions or DEFAULT_PERMISSIONS
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
        'buttons': buttons,
        'isAddonRoot': True,
        'permissions': permissions,
        'accept': {
            'maxSize': node_settings.config.max_file_size,
            'acceptedFiles': node_settings.config.accept_extensions
        },
        'urls': urls,
        'isPointer': False,
    }
    rv.update(kwargs)
    return rv


def build_addon_button(text, action):
    """Builds am action button to be rendered in HGrid

    :param str text: A string or html to appear on the button itself
    :param str action: The name of the HGrid action for the button to call.
        The callback for the HGrid action must be defined as a member of HGrid.Actions
    :return dict: Hgrid formatted dictionary for custom buttons

    """
    return {
        'text': text,
        'action': action,
    }


class NodeFileCollector(object):

    """A utility class for creating rubeus formatted node data"""

    def __init__(self, node, auth, **kwargs):
        self.node = node
        self.auth = auth
        self.extra = kwargs
        self.can_view = node.can_view(auth)
        self.can_edit = node.can_edit(auth) and not node.is_registration

    def to_hgrid(self):
        """Return the Rubeus.JS representation of the node's file data, including
        addons and components
        """
        root = self._serialize_node(self.node)
        return [root]

    def _collect_components(self, node, visited):
        rv = []
        for child in node.nodes:
            if child.resolve()._id not in visited and not child.is_deleted and node.can_view(self.auth):
                visited.append(child.resolve()._id)
                rv.append(self._serialize_node(child, visited=visited))
        return rv

    def _serialize_node(self, node, visited=None):
        """Returns the rubeus representation of a node folder.
        """
        visited = visited or []
        visited.append(node.resolve()._id)
        can_edit = node.can_edit(auth=self.auth) and not node.is_registration
        can_view = node.can_view(auth=self.auth)
        if can_view:
            children = self._collect_addons(node) + self._collect_components(node, visited)
        else:
            children = []
        return {
            'name': u'{0}: {1}'.format(node.project_or_component.capitalize(), node.title)
                if can_view
                else u'Private Component',
            'kind': FOLDER,
            'permissions': {
                'edit': can_edit,
                'view': can_view,
            },
            'urls': {
                'upload': os.path.join(node.api_url, 'osffiles') + '/',
                'fetch': None,
            },
            'children': children,
            'isPointer': not node.primary,
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
        'tree_js': list(collect_addon_js(node)),
        'tree_css': list(collect_addon_css(node)),
    }


# TODO: Abstract static collectors
def collect_addon_js(node, visited=None):
    """Collect JavaScript includes for all add-ons implementing HGrid views.

    :return list: List of JavaScript include paths

    """
    # NOTE: must coerce to list so it is JSON-serializable
    visited = visited or []
    visited.append(node._id)
    js = set()
    for addon in node.get_addons():
        js = js.union(addon.config.include_js.get('files', []))
    for each in node.nodes:
        if each._id not in visited:
            visited.append(each._id)
            js = js.union(collect_addon_js(each, visited=visited))
    return js


def collect_addon_css(node, visited=None):
    """Collect CSS includes for all addons-ons implementing Hgrid views.

    :return list: List of CSS include paths

    """
    visited = visited or []
    visited.append(node._id)
    css = set()
    for addon in node.get_addons():
        css = css.union(addon.config.include_css.get('files', []))
    for each in node.nodes:
        if each._id not in visited:
            visited.append(each._id)
            css = css.union(collect_addon_css(each, visited=visited))
    return css
