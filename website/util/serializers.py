from datetime import datetime

from website.project.model import Node

def delta_date(d):
    diff = d - datetime.utcnow()
    s = diff.total_seconds()
    return s

class NodeSerializer(object):

    def __init__(self, auth):
        self.auth = auth

    def _serialize_urls(self, node):
        can_view = node.can_view(self.auth)
        maybe_hide = lambda prop, default='': prop if can_view else default
        return {
            'api': maybe_hide(node.api_url, None),
            'web': maybe_hide(node.url, None),
            'upload': None,
            'fetch': maybe_hide((node.url if not node.is_folder else None), None),
        }

    def _serialize_permissions(self, node):
        return {
            'edit': node.can_edit(self.auth),
            'view': node.can_view(self.auth),
        }

    def _serialize_children(self, node):
        return []

    def _count_children(self, node):
        return len(node.next_descendants(self.auth, condition=lambda auth, n: n.is_contributor(auth.user)))

    def _serialize_contributors(self, node):
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
        return contributors

    def serialize(self, node, include_children=True):
        proper_category = Node.CATEGORY_MAP[node.category]
        can_view = node.can_view(self.auth)

        maybe_hide = lambda prop, default='': prop if can_view else default

        return {
            'name': (
                node.title.replace('&amp;', '&')
                if can_view
                else u"Private {0}".format(proper_category)
            ),
            'category': '_'.join(node.category.split(' ')),
            'isRegistration': node.is_registration,
            'registeredMeta': maybe_hide(node.registered_meta, {}),
            'node_id': maybe_hide(node.resolve()._id),
            'description': maybe_hide(node.description),
            'permissions': self._serialize_permissions(node),
            'urls': self._serialize_urls(node),
            'children': (
                self._serialize_children(node)
                if include_children
                else []
            ),
            'childrenCount': self._count_children(node),
            'contributors': self._serialize_contributors(node),
        }

class ProjectOrganizerSerializer(NodeSerializer):

    FOLDER = 'folder'

    def _serialize_permissions(self, node):
        ret = super(ProjectOrganizerSerializer, self)._serialize_permissions(node)
        parent = node.parent_node
        ret.update({
            'copyable': not node.is_folder,
            'movable': parent and parent.is_folder,
            'acceptsFolders': node.is_folder,
            'acceptsMoves': node.is_folder,
            'acceptsCopies': node.is_folder,
            'acceptsComponents': node.is_folder,
        })
        return ret

    def _do_serialize_children(self, pair):
        ret = self.serialize(pair[0])
        ret.update({
            'children': [self._do_serialize_children(child) for child in pair[1]]
        })
        return ret

    def _serialize_children(self, node):
        return [self._do_serialize_children(pair) for pair in node.next_descendants(
            self.auth,
            condition=lambda auth, n: n.is_contributor(auth.user)
        )]

    def serialize(self, node, include_children=True):
        ret = super(ProjectOrganizerSerializer, self).serialize(node)

        parent = node.parent_node

        date_modified = node.date_modified.isoformat()
        modified_delta = delta_date(node.date_modified)
        modified_by = ''
        try:
            user = node.logs[-1].user
            modified_by = user.family_name or user.given_name
        except AttributeError:
            modified_by = ''
            modified_delta = delta_date(node.date_modified)

        node_type = 'project'
        is_project = node.category == 'project'
        is_pointer = not node.primary and (parent and not parent.is_folder)
        is_component = not is_project and not is_pointer
        if is_pointer:
            node_type = 'pointer'
        if node.is_folder:
            node_type = 'folder'
        if is_component:
            node_type = 'component'

        if node.is_dashboard:
            to_expand = True
        elif node_type != 'pointer':
            to_expand = node.is_expanded(user=self.auth.user)
        else:
            to_expand = False

        ret.update({
            'kind': self.FOLDER,
            'type': node_type,
            'expand': to_expand,
            'dateModified': date_modified,
            'modifiedBy': modified_by,
            'modifiedDelta': modified_delta,
            'isProject': is_project,
            'isPointer': is_pointer,
            'isComponent': is_component,
            'isFile': False,
            'isFolder': node.is_folder,
            'isDashboard': node.is_dashboard,
            'isSmartFolder': False,
            'parentIsFolder': parent and parent.is_folder,
        })
        return ret

    def make_smart_folder(self, title, node_id, children_count):
        return {
            'name': title,
            'kind': 'folder',
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
