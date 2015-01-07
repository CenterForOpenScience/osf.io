#!/usr/bin/env python
# encoding: utf-8

"""Contains helper functions for generating correctly
formatted hgrid list/folders.
"""
import os
import datetime

import hurry
from modularodm import Q

from framework.auth.decorators import Auth
from website import settings
from website.settings import (
    ALL_MY_PROJECTS_ID, ALL_MY_REGISTRATIONS_ID, ALL_MY_PROJECTS_NAME,
    ALL_MY_REGISTRATIONS_NAME
)


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
            'acceptedFiles': node_settings.config.accept_extensions,
        },
        'urls': urls,
        'isPointer': False,
    }
    rv.update(kwargs)
    return rv


def build_addon_button(text, action, title=""):
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

class NodeProjectCollector(object):

    """A utility class for creating rubeus formatted node data for project organization"""
    def __init__(self, node, auth, just_one_level=False, **kwargs):
        self.node = node
        self.auth = auth
        self.extra = kwargs
        self.can_view = node.can_view(auth)
        self.can_edit = node.can_edit(auth) and not node.is_registration
        self.just_one_level = just_one_level

    def _collect_components(self, node, visited):
        rv = []
        for child in reversed(node.nodes):  # (child.resolve()._id not in visited or node.is_folder) and
            if child is not None and not child.is_deleted and child.resolve().can_view(auth=self.auth) and node.can_view(self.auth):
                # visited.append(child.resolve()._id)
                rv.append(self._serialize_node(child, visited=None, parent_is_folder=node.is_folder))
        return rv

    def collect_all_projects_smart_folder(self):
        contributed = self.auth.user.node__contributed
        all_my_projects = contributed.find(
            Q('category', 'eq', 'project') &
            Q('is_deleted', 'eq', False) &
            Q('is_registration', 'eq', False) &
            Q('is_folder', 'eq', False) &
            # parent is not in the nodes list
            Q('__backrefs.parent.node.nodes', 'eq', None)
        )
        comps = contributed.find(
            # components only
            Q('category', 'ne', 'project') &
            # parent is not in the nodes list
            Q('__backrefs.parent.node.nodes', 'nin', all_my_projects.get_keys()) &
            # exclude deleted nodes
            Q('is_deleted', 'eq', False) &
            # exclude registrations
            Q('is_registration', 'eq', False)
        )
        children_count = all_my_projects.count() + comps.count()
        return self.make_smart_folder(ALL_MY_PROJECTS_NAME, ALL_MY_PROJECTS_ID, children_count)

    def collect_all_registrations_smart_folder(self):
        contributed = self.auth.user.node__contributed
        all_my_registrations = contributed.find(
            Q('category', 'eq', 'project') &
            Q('is_deleted', 'eq', False) &
            Q('is_registration', 'eq', True) &
            Q('is_folder', 'eq', False) &
            # parent is not in the nodes list
            Q('__backrefs.parent.node.nodes', 'eq', None)
        )
        comps = contributed.find(
            # components only
            Q('category', 'ne', 'project') &
            # parent is not in the nodes list
            Q('__backrefs.parent.node.nodes', 'nin', all_my_registrations.get_keys()) &
            # exclude deleted nodes
            Q('is_deleted', 'eq', False) &
            # exclude registrations
            Q('is_registration', 'eq', True)
        )
        children_count = all_my_registrations.count() + comps.count()
        return self.make_smart_folder(ALL_MY_REGISTRATIONS_NAME, ALL_MY_REGISTRATIONS_ID, children_count)

    def make_smart_folder(self, title, node_id, children_count=0):
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
            'type': 'smart-folder',
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
            'childrenCount': children_count,
        }
        return return_value

    def get_root(self):
        root = self._serialize_node(self.node, visited=None, parent_is_folder=False)
        return root

    def to_hgrid(self):
        """Return the Rubeus.JS representation of the node's children, not including addons
        """
        root = self._collect_components(self.node, visited=None)
        # This will be important when we mix files and projects together: self._collect_addons(self.node) +
        if self.node.is_dashboard:
            root.insert(0, self.collect_all_projects_smart_folder())
            root.insert(0, self.collect_all_registrations_smart_folder())
        return root

    def _serialize_node(self, node, visited=None, parent_is_folder=False):
        """Returns the rubeus representation of a node folder for the project organizer.
        """
        visited = visited or []
        visited.append(node.resolve()._id)
        can_edit = node.can_edit(auth=self.auth) and not node.is_registration
        expanded = node.is_expanded(user=self.auth.user)
        can_view = node.can_view(auth=self.auth)
        children = []
        modified_delta = delta_date(node.date_modified)
        date_modified = node.date_modified.isoformat()
        contributors = []
        for contributor in node.contributors:
            if contributor._id in node.visible_contributor_ids:
                contributor_name = [
                    contributor.family_name,
                    contributor.given_name,
                    contributor.fullname,
                ]
                contributors.append({
                    'name': next(name for name in contributor_name if name),
                    'url': contributor.url,
                })
        try:
            user = node.logs[-1].user
            modified_by = user.family_name
        except AttributeError:
            modified_by = ''
        # test_children = self._collect_addons(node)
        child_nodes = node.nodes
        readable_children = []
        for child in child_nodes:
            if child is not None:
                if child.resolve().can_view(auth=self.auth):
                    readable_children.append(child)
        children_count = len(readable_children)
        is_pointer = not node.primary
        is_component = node.category != "project"
        is_project = node.category == "project"
        is_file = False
        type_ = "project"
        if is_file:
            type_ = "file"
        if is_pointer and not parent_is_folder:
            type_ = "pointer"
        if node.is_folder:
            type_ = "folder"
        if is_component:
            type_ = "component"

        if node.is_dashboard:
            to_expand = True
        elif type_ != "pointer":
            to_expand = expanded
        else:
            to_expand = False

        return {
            'name': node.title if can_view else u'Private Component',
            'kind': FOLDER,
            # Once we get files into the project organizer, files would be kind of FILE
            'permissions': {
                'edit': can_edit,
                'view': can_view,
                'copyable': not node.is_folder,
                'movable': parent_is_folder,
                'acceptsFolders': node.is_folder,
                'acceptsMoves': node.is_folder,
                'acceptsCopies': node.is_folder or is_project,
                'acceptsComponents': node.is_folder,
            },
            'urls': {
                'upload': None,
                'fetch': node.url if not node.is_folder else None,
            },
            'type': type_,
            'children': children,
            'expand': to_expand,
            # TODO: (bgeiger) replace these flags with a Kind property or something
            'isProject': is_project,
            'isPointer': is_pointer,
            'isComponent': is_component,
            'isFolder': node.is_folder,
            'isDashboard': node.is_dashboard,
            'isFile': is_file,
            'dateModified': date_modified,
            'modifiedDelta': max(1, modified_delta),
            'modifiedBy': modified_by,
            'parentIsFolder': parent_is_folder,
            'contributors': contributors,
            'node_id': node.resolve()._id,
            'isSmartFolder': False,
            'apiURL': node.api_url,
            'isRegistration': node.is_registration,
            'description': node.description,
            'registeredMeta': node.registered_meta,
            'childrenCount': children_count,
        }

    def _collect_addons(self, node):
        return_value = []
        for addon in node.get_addons():
            if addon.config.has_hgrid_files:
                temp = self._upgrade_addon_meta(addon.config.get_hgrid_data(addon, self.auth, **self.extra))
                for item in temp:
                    item["node_id"] = node._id
                    item["apiURL"] = node.api_url
                return_value.extend(temp or [])
        return return_value

    def _upgrade_addon_meta(self, data):
        for datum in data:
            datum["expand"] = False
            datum["isProject"] = False
            datum["isPointer"] = False
            datum["isComponent"] = False
            datum["isFolder"] = False
            datum["isDashboard"] = False
            datum["isFile"] = True
            datum["dateModified"] = None
            datum["modifiedDelta"] = 0
            datum["modifiedBy"] = ""
            datum["parentIsFolder"] = False
            datum["contributors"] = []
            datum["isSmartFolder"] = False
            datum["isRegistration"] = False
            datum["description"] = ""
            datum["registeredMeta"] = {}
            datum["permissions"]["copyable"] = False
            datum["permissions"]["movable"] = False
            datum["permissions"]["acceptsFolders"] = False
            datum["permissions"]["acceptsMoves"] = False
            datum["permissions"]["acceptsCopies"] = False
            datum["permissions"]["acceptsComponents"] = False

        return data


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
                'edit': False,
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
                # WARNING: get_hgrid_data can return None if the addon is added but has no credentials.
                temp = addon.config.get_hgrid_data(addon, self.auth, **self.extra)
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
    # NOTE: must coerce to list so it is JSON-serializable
    visited = visited or []
    visited.append(node._id)
    js = set()
    for addon in node.get_addons():
        # JS modules configured in each addon's __init__ file
        js = js.union(addon.config.include_js.get(config_entry, []))
        # Webpack bundle
        file_path = os.path.join('static',
                                 'public',
                                 'js',
                                 addon.config.short_name,
                                 filename)
        js_file = os.path.join(
            settings.BASE_PATH, file_path
        )
        if os.path.exists(js_file):
            js_path = os.path.join('/', file_path)
            js.add(js_path)
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
