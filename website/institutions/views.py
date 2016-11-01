import httplib as http

from .model import Institution
from framework.exceptions import HTTPError

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from website.project.model import Node


def view_institution(inst_id, **kwargs):
    try:
        inst = Institution.find_one(Q('_id', 'eq', inst_id) & Q('is_deleted', 'ne', True))
    except NoResultsFound:
        raise HTTPError(http.NOT_FOUND)

    # The total number of affiliated nodes for each institution is calculated and cached
    # in the Institution.num_nodes (aka Node.institution_num_nodes) field.
    num_nodes = len(Node.find_by_institutions(inst, query=(
        Q('is_public', 'eq', True) &
        Q('is_folder', 'ne', True) &
        Q('is_deleted', 'ne', True) &
        Q('parent_node', 'eq', None) &
        Q('is_registration', 'eq', False)
    )))
    inst.node.institution_num_nodes = num_nodes
    inst.node.save()

    return {
        'id': inst._id,
        'name': inst.name,
        'logo_path': inst.logo_path,
        'logo_path_rounded_corners': inst.logo_path_rounded_corners,
        'description': inst.description or '',
        'banner_path': inst.banner_path
    }
