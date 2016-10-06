from website import settings
from website.project import Node
from website.project import utils

from modularodm.query.querydialect import DefaultQueryDialect as Q


def activity():

    node_data = utils.get_node_data()
    if node_data:
        hits = utils.hits(node_data)
    else:
        hits = {}

    # New Projects
    new_and_noteworthy_pointers = Node.find_one(Q('_id', 'eq', settings.NEW_AND_NOTEWORTHY_LINKS_NODE)).nodes_pointer
    new_and_noteworthy_projects = [pointer.node for pointer in new_and_noteworthy_pointers]

    # Popular Projects
    popular_public_projects = Node.find_one(Q('_id', 'eq', settings.POPULAR_LINKS_NODE)).nodes_pointer

    # Popular Registrations
    popular_public_registrations = Node.find_one(Q('_id', 'eq', settings.POPULAR_LINKS_NODE_REGISTRATIONS)).nodes_pointer

    return {
        'new_and_noteworthy_projects': new_and_noteworthy_projects,
        'recent_public_registrations': utils.recent_public_registrations(),
        'popular_public_projects': popular_public_projects,
        'popular_public_registrations': popular_public_registrations,
        'hits': hits,
    }
