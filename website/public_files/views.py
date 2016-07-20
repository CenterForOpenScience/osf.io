import httplib as http

from website.project.model import Node
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

@must_be_logged_in
def view_public_files(auth, **kwargs):

    user = auth.user
    try:
        publicFilesNode = Node.find_one(Q('is_public_files_collection', 'eq', True) & Q('contributors', 'eq', user._id))
    except NoResultsFound:
        raise HTTPError(http.NOT_FOUND)

    return serialize_public_files_node(publicFilesNode)

def view_public_files_id(uid, **kwargs):

    try:
        publicFilesNode = Node.find_one(Q('is_public_files_collection', 'eq', True) & Q('contributors', 'eq', uid))
    except NoResultsFound:
        raise HTTPError(http.NOT_FOUND)

    return serialize_public_files_node(publicFilesNode)

def serialize_public_files_node(node):

    return {
        'node':
            {
                'node_id': node._id,
                'api_url': node.api_url,
                'owner_name': node.creator.fullname,
                'is_public_files_node': node.is_public_files_collection,
            }
    }
