from modularodm import Q

from website.app import init_app
from website.models import User, Node, Institution


def get_institutions():
    institutions = Institution.find(Q('_id', 'ne', None))
    return institutions


def get_user_count_by_institutions():
    institutions = get_institutions()
    user_counts = []
    for institution in institutions:
        query = Q('_affiliated_institutions', 'eq', institution.node)
        user_counts.append({institution.name: User.find(query).count()})
    return user_counts


def get_node_count_by_institutions():
    institutions = get_institutions()
    node_counts = []
    for institution in institutions:
        query = (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'ne', True) &
            Q('parent_node', 'eq', None)
        )
        node_counts.append({institution.name: Node.find_by_institutions(institution, query).count()})
    return node_counts


def main():
    users_by_institutions = get_user_count_by_institutions()
    nodes_by_institutions = get_node_count_by_institutions()
    print(users_by_institutions)
    print(nodes_by_institutions)


if __name__ == '__main__':
    init_app()
    main()
