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
            Q('is_folder', 'ne', True)
        )

        registration_query = node_query & Q('is_registration', 'eq', True)
        non_registration_query = node_query & Q('is_registration', 'eq', False)
        project_query = non_registration_query & Q('parent_node', 'eq', None)
        registered_project_query = registration_query & Q('parent_node', 'eq', None)
        public_query = Q('is_public', 'eq', True)
        private_query = Q('is_public', 'eq', False)
        node_public_query = non_registration_query & public_query
        node_private_query = non_registration_query & private_query
        project_public_query = project_query & public_query
        project_private_query = project_query & private_query
        registered_node_public_query = registration_query & public_query
        registered_node_private_query = registration_query & private_query
        registered_project_public_query = registered_project_query & public_query
        registered_project_private_query = registered_project_query & private_query
        count = {
            'institution':{
                'id': institution._id,
                'name': institution.name,
            },
            'users': {
                'total': User.find(user_query).count(),
            },
            'nodes': {
                'total':Node.find_by_institutions(institution, node_query).count(),
                'public': Node.find_by_institutions(institution, node_public_query).count(),
                'private': Node.find_by_institutions(institution, node_private_query).count(),
            },
            'projects': {
                'total': Node.find_by_institutions(institution, project_query).count(),
                'public': Node.find_by_institutions(institution, project_public_query).count(),
                'private': Node.find_by_institutions(institution, project_private_query).count(),
            },
            'registered_nodes': {
                'total': Node.find_by_institutions(institution, registration_query).count(),
                'public': Node.find_by_institutions(institution, registered_node_public_query).count(),
                'embargoed': Node.find_by_institutions(institution, registered_node_private_query).count(),
            },
            'registered_projects': {
                'total': Node.find_by_institutions(institution, registered_project_query).count(),
                'public': Node.find_by_institutions(institution, registered_project_public_query).count(),
                'embargoed': Node.find_by_institutions(institution, registered_project_private_query).count(),
            },
        }
        counts.append(count)
    keen_payload = {'institution_analytics': counts}
    return keen_payload


def main():
    counts_by_institutions = get_count_by_institutions()
    keen_project = keen_settings['private']['project_id']
    write_key = keen_settings['private']['write_key']
    if keen_project and write_key:
        client = KeenClient(
            project_id=keen_project,
            write_key=write_key,
        )
        client.add_events(counts_by_institutions)
    else:
        print(counts_by_institutions)


if __name__ == '__main__':
    init_app()
    main()
