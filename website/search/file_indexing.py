import logging

from framework.sentry import log_exception
from website import search
from website.search import tasks


logger = logging.getLogger(__name__)


def except_search_unavailable(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except search.exceptions.SearchUnavailableError as e:
            logger.exception(e)
            log_exception()
    return wrapper


@except_search_unavailable
def update_search_files(node):
    """Update all files associated with node based on node's privacy.
    """
    if node.is_public:
        tasks.queue_update_all_files(node)
        # tasks.enqueue_task(tasks.update_all_files_task.s(self))


@except_search_unavailable
def delete_search_files(node):
    tasks.queue_delete_all_files(node)
    # tasks.enqueue_task(tasks.delete_all_files_task.s(self))


@except_search_unavailable
def update_search_file(file_node):
    """ Update a single file in the node based on the action given.
    """
    if file_node.node.is_public:
        tasks.queue_update_file(file_node)
        # tasks.enqueue_task(tasks.update_file_task.s(file_node))


@except_search_unavailable
def delete_search_file(file_node):
    tasks.queue_delete_file(file_node)
    # tasks.enqueue_task(tasks.delete_file_task.s(file_node))
