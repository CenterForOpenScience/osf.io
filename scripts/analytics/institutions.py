from modularodm import Q

from website.app import init_app
from website.models import User, Node, Institution
from website.settings import KEEN as keen_settings
from keen.client import KeenClient


def get_institutions():
    institutions = Institution.find(Q('_id', 'ne', None))
    return institutions


def get_count_by_institutions():
    institutions = get_institutions()
    counts = []

    for institution in institutions:
        user_query = Q('_affiliated_institutions', 'eq', institution.node)
        node_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'ne', True) &
            Q('parent_node', 'eq', None)
        )
        count = {
            'institution': institution.name,
            'users': User.find(user_query).count(),
            'nodes': Node.find_by_institutions(institution, node_query).count(),
        }
        counts.append(count)
    keen_payload = {'institution_analytics': counts}
    return keen_payload


def main():
    counts_by_institutions = get_count_by_institutions()
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    read_key = keen_settings['private']['read_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
            read_key=read_key
        )
        client.add_events(counts_by_institutions)
    else:
        print(counts_by_institutions)


if __name__ == '__main__':
    init_app()
    main()
