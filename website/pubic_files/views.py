import httplib as http

from website.project.model import Node
from modularodm import Q
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

@must_be_logged_in
def view_public_files(auth, **kwargs):

    user = auth.user
    publicFilesCollection = Node.find_one(Q('is_public_files_collection', 'eq', True) & Q('contributors', 'eq', user._id))

    if not publicFilesCollection:
        raise HTTPError(http.NOT_FOUND)
    return {
        'node':
            {
                'id': publicFilesCollection._id,
                'api_url': publicFilesCollection.api_url,
                'ownerName': publicFilesCollection.creator.fullname,
                'isPublicFilesCol': publicFilesCollection.is_public_files_collection,
            }
    }

def view_public_files_id(uid, **kwargs):

    publicFilesCollection = Node.find_one(Q('is_public_files_collection', 'eq', True) & Q('contributors', 'eq', uid))

    if not publicFilesCollection:
        raise HTTPError(http.NOT_FOUND)
    return {
        'node':
            {
                'id': publicFilesCollection._id,
                'api_url': publicFilesCollection.api_url,
                'ownerName': publicFilesCollection.creator.fullname,
                'isPublicFilesCol': publicFilesCollection.is_public_files_collection,
            }
    }
