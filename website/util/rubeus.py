# -*- coding: utf-8 -*-
"""Contanins Helper functions for generating correctly
formated hgrid list/folders.
"""
import json
import itertools

#TODO Fix me, circular import. Still works for some reason....
from website.project.views.node import _view_project
from framework.auth.decorators import Auth

# Rubeus defined Constants
FOLDER = 'folder'
FILE = 'item'
KIND = 'kind'

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
    name = node_settings.config.full_name + ': ' + \
        name if name else node_settings.config.full_name
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

    def __init__(self, node, auth, parent=None, **kwargs):
        self.node = node
        self.auth = auth
        self.parent = parent
        self.extra = kwargs
        self.can_view = node.can_view(auth)
        self.can_edit = node.can_edit(auth) if self.can_view else False

    def __call__(self, mode):
        """calls the to_hgrid method"""
        return self.to_hgrid(mode)

    def to_hgrid(self, mode):
        if mode == 'page':
            return self.to_hgrid_page()
        elif mode == 'widget':
            return self.to_hgrid_widget()
        else:
            return self.to_hgrid_other()

    def to_hgrid_page(self):
        rv = _view_project(self.node, self.auth, **self.extra)
        rv.update({
            'grid_data': self._get_grid_data(),
            'tree_js': self._collect_static_js(),
            'tree_css': self._collect_static_css()
        })
        return rv

    def to_hgrid_widget(self):
        return {'grid_data': self._get_grid_data()}

    def to_hgrid_other(self):
        return self._get_grid_data()

    def _collect_components(self, node):
        rv = []
        for child in node.nodes:
            if not child.is_deleted:
                rv.append(self._create_dummy(child))
        return rv

    def _get_grid_data(self):
        return json.dumps(self._collect_addons(self.node) + self._collect_components(self.node))

    def _create_dummy(self, node):
        return {
            'name': 'Component: {0}'.format(node.title) if self.can_view else 'Private Component',
            'kind': FOLDER,
            'permissions': {
                'edit': self.can_edit,
                'view': self.can_view
            },
            'urls': {
                'upload': None,
                'fetch': None
            },
            'children': self._collect_addons(node) + self._collect_components(node)
        }

    def _collect_addons(self, node):
        rv = []
        for addon in node.get_addons():
            if addon.config.has_hgrid_files:
                temp = addon.config.get_hgrid_data(addon, self.auth, **self.extra)
                if temp:
                    temp['iconUrl'] = addon.config.icon_url
                    rv.append(temp)
        return rv

    def _collect_static_js(self):
        """Collect JavaScript includes for all add-ons implementing HGrid views.

        :return list: List of JavaScript include paths

        """
        return itertools.chain.from_iterable(
            addon.config.include_js.get('files', [])
            for addon in self.node.get_addons()
        )

    def _collect_static_css(self):
        """Collect CSS includes for all addons-ons implementing Hgrid views.

        :return list: List of CSS include paths

        """
        return itertools.chain.from_iterable(
            addon.config.include_css.get('files', [])
            for addon in self.node.get_addons()
        )
