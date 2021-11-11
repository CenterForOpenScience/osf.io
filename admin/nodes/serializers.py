from osf.models import Contributor


def serialize_simple_user_and_node_permissions(node, user):
    """
    Permission is perm user has through contributorship, not group membership
    """
    return {
        'id': user._id,
        'name': user.fullname,
        'permission': Contributor.objects.get(user_id=user.id, node_id=node.id).permission
    }

def serialize_groups_for_node(node, osf_group):
    return {
        'name': osf_group.name,
        'id': osf_group._id,
        'permission': osf_group.get_permission_to_node(node)
    }
