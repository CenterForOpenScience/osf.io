import logging

from framework.sentry import log_exception
from website import search
from website.search import tasks
from website.search import file_util


logger = logging.getLogger(__name__)


def except_search_unavailable(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()
    return wrapper


@file_util.require_file_indexing
@except_search_unavailable
def update_search_files(node):
    """Update all files associated with node based on node's privacy.
    """
    if node.is_public:
        tasks.update_all_files_task(node=node)


@except_search_unavailable
def delete_search_files(node):
    search.search.delete_all_files(node)


@file_util.require_file_indexing
@except_search_unavailable
def update_search_file(file_node):
    """ Update a single file in the node based on the action given.
    """
    if file_node.node.is_public:
        nid = file_node._id
        url = file_util.get_file_content_url(file_node)
        tasks.update_file_task.delay(file_node_id=nid, file_url=url)


@file_util.require_file_indexing
@except_search_unavailable
def delete_search_file(file_node):
    path = file_node.path
    parent_id = file_node.node._id
    tasks.delete_file_task.delay(file_node_id=path, parent_id=parent_id)
