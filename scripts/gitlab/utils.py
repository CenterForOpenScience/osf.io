import os
import logging
import subprocess
from dulwich.repo import Repo
from dulwich.errors import NotGitRepository

from website import settings


logger = logging.getLogger(__name__)


def get_node_path(node):
    return os.path.join(settings.UPLOADS_PATH, node._id)

def get_node_repo(node):

    if not node.files_current:
        return None

    path = get_node_path(node)

    if not os.path.exists(path):
        logging.warn('No folder found for node {0}'.format(node._id))
        return None

    try:
        return Repo(path)
    except NotGitRepository:
        logging.warn('No repo found for node {0}'.format(node._id))
        return None

def get_file_commits(node, file):

    try:
        output = subprocess.check_output(
            ['git', 'rev-list', '--all', '--reverse', file],
            cwd=get_node_path(node)
        )
    except subprocess.CalledProcessError as error:
        logger.error(error)
        raise
        # if error.status_code ...
        # return []

    return output.strip().split('\n')
