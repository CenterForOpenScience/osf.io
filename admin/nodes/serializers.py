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
