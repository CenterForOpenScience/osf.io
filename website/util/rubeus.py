# -*- coding: utf-8 -*-
"""Contains helper functions for generating correctly
formatted hgrid list/folders.
"""
import logging
import datetime

import hurry.filesize

from framework import sentry
from framework.auth.decorators import Auth

from website import settings
from website.util import paths
from website.util import sanitize
from website.settings import DISK_SAVING_MODE


logger = logging.getLogger(__name__)

FOLDER = 'folder'
FILE = 'file'
KIND = 'kind'

# TODO: Validate the JSON schema, esp. for addons

DEFAULT_PERMISSIONS = {
    'view': True,
    'edit': False,
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
                     urls=None, extra=None, buttons=None, user=None,
                     private_key=None, **kwargs):
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
    :param bool private_key: Used to check if information should be stripped from anonymous links
    :param dict kwargs: Any additional information to add to the root folder
    :return dict: Hgrid formatted dictionary for the addon root folder

    """
    from website.util import check_private_key_for_anonymized_link

    permissions = permissions or DEFAULT_PERMISSIONS
    if name and not check_private_key_for_anonymized_link(private_key):
        name = u'{0}: {1}'.format(node_settings.config.full_name, name)
    else:
        name = node_settings.config.full_name
    if hasattr(node_settings.config, 'urls') and node_settings.config.urls:
        urls = node_settings.config.urls
    if urls is None:
        urls = default_urls(node_settings.owner.api_url, node_settings.config.short_name)

    forbid_edit = DISK_SAVING_MODE if node_settings.config.short_name == 'osfstorage' else False
    if isinstance(permissions, Auth):
        auth = permissions
        permissions = {
            'view': node_settings.owner.can_view(auth),
            'edit': (node_settings.owner.can_edit(auth)
                     and not node_settings.owner.is_registration
                     and not forbid_edit),
        }

    max_size = node_settings.config.max_file_size
    if user and 'high_upload_limit' in user.system_tags:
        max_size = node_settings.config.high_max_file_size

    ret = {
        'provider': node_settings.config.short_name,
        'addonFullname': node_settings.config.full_name,
        'name': name,
        'iconUrl': node_settings.config.icon_url,
        KIND: FOLDER,
        'extra': extra,
        'buttons': buttons,
        'isAddonRoot': True,
        'permissions': permissions,
        'accept': {
            'maxSize': max_size,
            'acceptedFiles': node_settings.config.accept_extensions,
        },
        'urls': urls,
        'isPointer': False,
        'nodeId': node_settings.owner._id,
        'nodeUrl': node_settings.owner.url,
        'nodeApiUrl': node_settings.owner.api_url,
    }
    ret.update(kwargs)
    return ret


def build_addon_button(text, action, title=''):
    """Builds am action button to be rendered in HGrid

    :param str text: A string or html to appear on the button itself
    :param str action: The name of the HGrid action for the button to call.
        The callback for the HGrid action must be defined as a member of HGrid.Actions
    :return dict: Hgrid formatted dictionary for custom buttons

    """
    button = {
        'text': text,
        'action': action,
    }
    if title:
        button['attributes'] = 'title="{title}" data-toggle="tooltip" data-placement="right" '.format(title=title)
    return button


def sort_by_name(hgrid_data):
    return_value = hgrid_data
    if hgrid_data is not None:
        return_value = sorted(hgrid_data, key=lambda item: item['name'].lower())
    return return_value


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
            if not child.can_view(self.auth):
                readable_descendants = child.find_readable_descendants(self.auth)
                for desc in readable_descendants:
                    visited.append(desc.resolve()._id)
                    rv.append(self._serialize_node(desc, visited=visited))
            elif child.resolve()._id not in visited and not child.is_deleted and node.can_view(self.auth):
                visited.append(child.resolve()._id)
                rv.append(self._serialize_node(child, visited=visited))
        return rv

    def _get_node_name(self, node):
        """Input node object, return the project name to be display.
        """
        can_view = node.can_view(auth=self.auth)

        if can_view:
            node_name = sanitize.unescape_entities(node.title)
        elif node.is_registration:
            node_name = u'Private Registration'
        elif node.is_fork:
            node_name = u'Private Fork'
        elif not node.primary:
            node_name = u'Private Link'
        else:
            node_name = u'Private Component'

        return node_name

    def _serialize_node(self, node, visited=None):
        """Returns the rubeus representation of a node folder.
        """
        visited = visited or []
        visited.append(node.resolve()._id)
        can_view = node.can_view(auth=self.auth)
        if can_view:
            children = self._collect_addons(node) + self._collect_components(node, visited)
        else:
            children = []

        return {
            # TODO: Remove safe_unescape_html when mako html safe comes in
            'name': self._get_node_name(node),
            'category': node.category,
            'kind': FOLDER,
            'permissions': {
                'edit': node.can_edit(self.auth) and not node.is_registration,
                'view': can_view,
            },
            'urls': {
                'upload': None,
                'fetch': None,
            },
            'children': children,
            'isPointer': not node.primary,
            'isSmartFolder': False,
            'nodeType': node.project_or_component,
            'nodeID': node.resolve()._id,
        }

    def _collect_addons(self, node):
        rv = []
        for addon in node.get_addons():
            if addon.config.has_hgrid_files:
                # WARNING: get_hgrid_data can return None if the addon is added but has no credentials.
                try:
                    temp = addon.config.get_hgrid_data(addon, self.auth, **self.extra)
                except Exception as e:
                    logger.warn(
                        getattr(
                            e,
                            'data',
                            'Unexpected error when fetching file contents for {0}.'.format(addon.config.full_name)
                        )
                    )
                    sentry.log_exception()
                    rv.append({
                        KIND: FOLDER,
                        'unavailable': True,
                        'iconUrl': addon.config.icon_url,
                        'provider': addon.config.short_name,
                        'addonFullname': addon.config.full_name,
                        'permissions': {'view': False, 'edit': False},
                        'name': '{} is currently unavailable'.format(addon.config.full_name),
                    })
                    continue
                rv.extend(sort_by_name(temp) or [])
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
def collect_addon_js(node, visited=None, filename='files.js', config_entry='files'):
    """Collect JavaScript includes for all add-ons implementing HGrid views.

    :return list: List of JavaScript include paths

    """
    js = []
    for addon_config in settings.ADDONS_AVAILABLE_DICT.values():
        # JS modules configured in each addon's __init__ file
        js.extend(addon_config.include_js.get(config_entry, []))
        # Webpack bundle
        js_path = paths.resolve_addon_path(addon_config, filename)
        if js_path:
            js.append(js_path)
    return js


def collect_addon_css(node, visited=None):
    """Collect CSS includes for all addons-ons implementing Hgrid views.

    :return: List of CSS include paths
    :rtype: list
    """
    css = []
    for addon_config in settings.ADDONS_AVAILABLE_DICT.values():
        # CSS modules configured in each addon's __init__ file
        css.extend(addon_config.include_css.get('files', []))
    return css


def delta_date(d):
    diff = d - datetime.datetime.utcnow()
    s = diff.total_seconds()
    return s
