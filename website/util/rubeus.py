# -*- coding: utf-8 -*-
"""Contains helper functions for generating correctly
formatted hgrid list/folders.
"""
import logging

from django.utils import timezone

from framework import sentry
from framework.auth.decorators import Auth

from django.apps import apps
from django.db.models import Exists, OuterRef

from website import settings
from website.util import paths
from website.settings import DISK_SAVING_MODE
from osf.utils import sanitize


logger = logging.getLogger(__name__)

FOLDER = 'folder'
FILE = 'file'
KIND = 'kind'

# TODO: Validate the JSON schema, esp. for addons

DEFAULT_PERMISSIONS = {
    'view': True,
    'edit': False,
}

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
        eg. Branch switcher for github/bitbucket/gitlab
    :param list of dicts buttons: List of buttons to appear in HGrid row. Each
        dict must have 'text', a string that will appear on the button, and
        'action', the name of a function in
    :param bool private_key: Used to check if information should be stripped from anonymous links
    :param dict kwargs: Any additional information to add to the root folder
    :return dict: Hgrid formatted dictionary for the addon root folder

    """
    from osf.utils.permissions import check_private_key_for_anonymized_link

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

    if hasattr(node_settings, 'region'):
        ret.update({'nodeRegion': node_settings.region.name})

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
        NodeRelation = apps.get_model('osf.NodeRelation')
        self.node = node.child if isinstance(node, NodeRelation) else node
        self.auth = auth
        self.extra = kwargs
        self.can_view = self.node.can_view(auth)
        self.can_edit = self.node.can_edit(auth) and not self.node.is_registration

    def to_hgrid(self):
        """
        Returns a representation of the node's file data, including
        addons and components. For efficiency, only the children and
        grandchildren of the node are serialized.
        """
        root = self._get_nodes(self.node, grid_root=self.node)
        return [root]

    def find_readable_descendants(self, node, visited):
        """
        Returns a generator of first descendant node(s) readable by <user>
        in each descendant branch.
        """
        new_branches = []
        Contributor = apps.get_model('osf.Contributor')

        linked_node_sqs = node.node_relations.filter(is_node_link=True, child=OuterRef('pk'))
        has_write_perm_sqs = Contributor.objects.filter(node=OuterRef('pk'), write=True, user=self.auth.user)
        descendants_qs = (
            node._nodes
            .filter(is_deleted=False)
            .annotate(is_linked_node=Exists(linked_node_sqs))
            .annotate(has_write_perm=Exists(has_write_perm_sqs))
            .order_by('_parents')
        )

        for descendant in descendants_qs:
            if descendant.can_view(self.auth):
                yield descendant
            elif descendant._id not in visited:
                new_branches.append(descendant)
                visited.append(descendant._id)

        for bnode in new_branches:
            for descendant in self.find_readable_descendants(bnode, visited=visited):
                yield descendant

    def _serialize_node(self, node, parent=None, grid_root=None, children=None):
        children = children or []
        is_pointer = parent and node.is_linked_node
        can_edit = node.has_write_perm if hasattr(node, 'has_write_perm') else node.can_edit(auth=self.auth)

        # Determines if `node` is within two levels of `grid_root`
        # Used to prevent complete serialization of deeply nested projects
        if parent and grid_root and parent == grid_root:
            children = self._get_nodes(node)['children']

        if not children:
            children = []

        return {
            # TODO: Remove safe_unescape_html when mako html safe comes in
            'name': sanitize.unescape_entities(node.title),
            'category': node.category,
            'kind': FOLDER,
            'permissions': {
                'edit': can_edit and not node.is_registration,
                'view': True,
            },
            'urls': {
                'upload': None,
                'fetch': None,
            },
            'children': children,
            'isPointer': is_pointer,
            'isSmartFolder': False,
            'nodeType': 'component' if parent else 'project',
            'nodeID': node._id,
        }

    def _get_nodes(self, node, grid_root=None):
        data = []
        if node.can_view(auth=self.auth):
            serialized_addons = self._collect_addons(node)
            serialized_children = [
                self._serialize_node(child, parent=node, grid_root=grid_root)
                for child in self.find_readable_descendants(node, visited=[])
            ]
            data = serialized_addons + serialized_children
        return self._serialize_node(node, children=data)

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
    diff = d - timezone.now()
    s = diff.total_seconds()
    return s
