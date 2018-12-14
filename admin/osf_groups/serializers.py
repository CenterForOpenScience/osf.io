from admin.users.serializers import serialize_user
from guardian.shortcuts import get_perms
from osf.utils import permissions


def serialize_group(osf_group):

    return {
        'id': osf_group._id,
        'name': osf_group.name,
        'created': osf_group.created,
        'modified': osf_group.modified,
        'creator': osf_group.creator,
        'managers': [serialize_user(user) for user in list(osf_group.managers.all())],
        'members': [serialize_user(user) for user in list(osf_group.members.all())],
        'members_only': [serialize_user(user) for user in list(osf_group.members_only.all())],
        'nodes': [serialize_node_for_groups(node, osf_group) for node in list(osf_group.nodes)]
    }


def serialize_node_for_groups(node, osf_group):
    return {
        'title': node.title,
        'id': node._id,
        'permission': permissions.reduce_permissions(get_perms(osf_group.member_group, node))
    }
