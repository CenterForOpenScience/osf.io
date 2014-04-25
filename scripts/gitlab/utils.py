import os
import logging
from dulwich.repo import Repo
from dulwich.errors import NotGitRepository

from website import settings

def get_node_repo(node):

    if not node.files_current:
        return None

    path = os.path.join(settings.UPLOADS_PATH, node._id)

    if not os.path.exists(path):
        logging.warn('No folder found for node {0}'.format(node._id))
        return None

    try:
        return Repo(path)
    except NotGitRepository:
        logging.warn('No repo found for node {0}'.format(node._id))
        return None
