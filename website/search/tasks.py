import celery
import logging
import requests

from framework.tasks import app
from website import settings
from website.search import search
from website.addons.osfstorage import model
from website.app import init_addons, do_set_backends
from website.search import file_util


logger = logging.getLogger(__name__)


@app.task
def update_file_task(file_node_id, file_url, index=None):
    logger.info('\n\nI do declare, Update File has been called!\n')

    init_addons(settings, routes=False)
    do_set_backends(settings)

    file_node = model.OsfStorageFileNode.load(file_node_id)

    content = requests.get(file_url).content

    return search.update_file_given_content(file_node, content, index)


@app.task
def delete_file_task(file_node_id, parent_id, index=None):
    logger.info('\n\n I do declare, Delete File has indeed been called!\n')

    init_addons(settings, routes=False)
    do_set_backends(settings)

    file_path = file_node_id
    return search.delete_file_given_path(file_path, file_parent_id=parent_id, index=index)


def update_all_files_task(node):
    file_gen = file_util.collect_files(node, recur=False)
    jobs = celery.group(update_file_task.si(fn._id, file_util.get_file_content_url(fn)) for fn in file_gen)
    jobs.delay()
    logger.info('\n\n I must acknowledge the fact that update all has been called!')


def delete_all_files_task(node):
    node_id = node._id
    file_gen = file_util.collect_files(node, recur=False)
    jobs = celery.group(delete_file_task.si(fn._id, node_id) for fn in file_gen)
    jobs.delay()
    logger.info('\n\n Verily I say, the task to delete all files of a node has been called!\n')
