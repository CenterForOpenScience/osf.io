from modularodm import Q

def get_all_projects_smart_folder(auth, **kwargs):
    # TODO: Unit tests
    user = auth.user

    contributed = user.node__contributed

    nodes = contributed.find(
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False) &
        Q('is_folder', 'eq', False)
    ).sort('-title')
    index = []
    ret = []
    for node in [n.root for n in nodes]:
        if node._id in index:
            continue
        index.append(node._id)
        ret.append(node)
    return ret

def get_all_registrations_smart_folder(auth, **kwargs):
    # TODO: Unit tests
    user = auth.user
    contributed = user.node__contributed

    nodes = contributed.find(
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', True) &
        Q('is_folder', 'eq', False)
    ).sort('-title')
    index = []
    ret = []
    for node in [n.root for n in nodes]:
        if node._id in index:
            continue
        index.append(node._id)
        ret.append(node)
    return ret

def get_dashboard_nodes(node, auth):
    rv = []
    for child in reversed(node.nodes):
        if child is not None and not child.is_deleted and child.resolve().can_view(auth=auth) and node.can_view(auth):
            rv.append(child)
    return rv
