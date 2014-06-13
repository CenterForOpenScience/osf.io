# -*- coding: utf-8 -*-
"""Contanins Helper functions for generating correctly
formated hgrid list/folders.
"""
import os
import hurry
import datetime
from framework.auth.decorators import Auth

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

    :param node Node: the node to be parsed
    :param auth Auth: the user authorization object
    :returns: rubeus-formatted dict

    """
    return NodeFileCollector(node, auth, **data).to_hgrid()

def to_project_hgrid(node, auth, **data):
    """Converts a node into a rubeus grid format

    :param node Node: the node to be parsed
    :param auth Auth: the user authorization object
    :returns: rubeus-formatted dict

    """
    return NodeProjectCollector(node, auth, **data).to_hgrid()

def to_project_root(node, auth, **data):
    return NodeProjectCollector(node, auth, **data).get_root()

def build_addon_root(node_settings, name, permissions=None,
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


class NodeProjectCollector(object):

    """A utility class for creating rubeus formatted node data for project organization"""
    def __init__(self, node, auth, **kwargs):
        self.node = node
        self.auth = auth
        self.extra = kwargs
        self.can_view = node.can_view(auth)
        self.can_edit = node.can_edit(auth) and not node.is_registration
        self.just_one_level = kwargs.get('just_one_level', False)

    def _collect_components(self, node, visited):
        rv = []
        for child in reversed(node.nodes): #(child.resolve()._id not in visited or node.is_folder) and
            if not child.is_deleted and node.can_view(self.auth):
                # visited.append(child.resolve()._id)
                rv.append(self._serialize_node(child, visited=None, parent_is_folder=node.is_folder))
        return rv


    def get_all_projects_smart_folder(self):
        return self.make_smart_folder('All my projects', '-amp')

    def get_all_registrations_smart_folder(self):
        return self.make_smart_folder('All my registrations', '-amr')

    def make_smart_folder(self, title, node_id):
        return_value = {
            'name': title,
            'kind': FOLDER,
            'permissions': {
                'edit': False,
                'view': True,
                'copyable': False,
                'movable': False,
                'acceptsDrops': False,
            },
            'urls': {
                'upload': None,
                'fetch': None,
            },
            'children': [],
            'expand': False,
            'isPointer': False,
            'isFolder': True,
            'isSmartFolder': True,
            'dateModified': None,
            'modifiedDelta': 0,
            'modifiedBy': None,
            'parentIsFolder': True,
            'isDashboard': False,
            'contributors': [],
            'node_id': node_id,
        }
        return return_value

    def get_root(self):
        root = self._serialize_node(self.node, visited=None, parent_is_folder=False)
        return root

    def to_hgrid(self):
        """Return the Rubeus.JS representation of the node's children, not including addons
        """
        root = self._collect_components(self.node, visited=None)
        if self.node.is_dashboard:
            root.append(self.get_all_projects_smart_folder())
            root.append(self.get_all_registrations_smart_folder())
        return root

    def _serialize_node(self, node, visited=None, parent_is_folder=False):
        """Returns the rubeus representation of a node folder for the project organizer.
        """
        visited = visited or []
        visited.append(node.resolve()._id)
        can_edit = node.can_edit(auth=self.auth) and not node.is_registration
        expanded = node.is_expanded(auth=self.auth)
        can_view = True # node.can_view(auth=self.auth)
        modified_delta = delta_date(node.date_modified)
        date_modified = node.date_modified.isoformat()
        contributors = [{'name': contributor.family_name, 'url': contributor.url} for contributor in node.contributors]
        modified_by = node.logs[-1].user.family_name
        children_count = len(node.nodes)
        if node.resolve().parent_id is None:
            is_project = True
        else:
            is_project = False
        is_pointer = not node.primary
        is_component = node.resolve().primary and not is_project

        if can_view and (node.primary or node.is_folder or parent_is_folder) and children_count > 0:
            children = True
        else:
            children = False
        return {
            'name': node.title
                if can_view
                else u'Private Component',
            'kind': FOLDER
                if (children or node.is_folder)
                else FILE,
            'permissions': {
                'edit': can_edit,
                'view': can_view,
                'copyable': False
                    if node.is_folder
                    else True,
                'movable': True
                    if parent_is_folder
                    else False,
                'acceptsFolders': True
                    if node.is_folder
                    else False,
                'acceptsMoves': True
                    if node.is_folder
                    else False,
                'acceptsCopies': True
                    if node.is_folder or is_project
                    else False,
                'acceptsComponents': True
                    if node.is_folder
                    else False,
            },
            'urls': {
                'upload': None,
                'fetch': node.url
                    if not node.is_folder
                    else None,
            },
            'children': [],
            'expand': True
                if node.is_dashboard
                else expanded,
            'isProject': is_project,
            'isPointer': is_pointer,
            'isComponent': is_component,
            'isFolder': node.is_folder,
            'dateModified': date_modified,
            'modifiedDelta': modified_delta,
            'modifiedBy': modified_by,
            'parentIsFolder': parent_is_folder,
            'isDashboard': node.is_dashboard,
            'contributors': contributors,
            'node_id': node.resolve()._id,
            'isSmartFolder': False,
            'apiURL': node.api_url,
            'isRegistration': node.is_registration,
            'description': node.description,
            'registeredMeta': node.registered_meta,
        }


class NodeFileCollector(object):

    """A utility class for creating rubeus formatted node data"""
    def __init__(self, node, auth, **kwargs):
        self.node = node
        self.auth = auth
        self.extra = kwargs
        self.can_view = node.can_view(auth)
        self.can_edit = node.can_edit(auth) and not node.is_registration

    def _collect_components(self, node, visited):
        rv = []
        for child in node.nodes:
            if child.resolve()._id not in visited and not child.is_deleted and node.can_view(self.auth):
                visited.append(child.resolve()._id)
                rv.append(self._serialize_node(child, visited=visited))
        return rv

    def to_hgrid(self):
        """Return the Rubeus.JS representation of the node's file data, including
        addons and components
        """
        root = self._serialize_node(self.node)
        return [root]

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
            'isSmartFolder': False,
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


def delta_date(d):
    diff = d - datetime.datetime.utcnow()
    s = diff.total_seconds()
    return s