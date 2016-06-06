import httplib as http

from .model import ShareWindow
from website.project.model import Node
from modularodm import Q
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in

@must_be_logged_in
def view_share_window(auth, **kwargs):

    user = auth.user
    shareWindow = ShareWindow.load(user._id)

    if not shareWindow:
        raise HTTPError(http.NOT_FOUND)
    return {
        'node':
            {
            'id': shareWindow._id,
            'api_url': shareWindow.api_url,
            'ownerName': shareWindow.creator.fullname,
             }
    }
