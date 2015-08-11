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

@app.task
def move_file_task(file_node_id, old_parent_id, new_parent_id):
    logger.info('\n\nIt is indeed the case that Mode File has been called\n')

    init_addons(settings, routes=False)
    do_set_backends(settings)
    return search.move_file(file_node_id, old_parent_id, new_parent_id)


@app.task
def copy_file_task(file_node_id, new_file_node_id, old_parent_id, new_parent_id):
    logger.info('\n\n I am proud to announce copy file\'s calling!')

    init_addons(settings, routes=False)
    do_set_backends(settings)
    return search.copy_file(file_node_id, new_file_node_id, old_parent_id, new_parent_id)


def update_all_files_task(node):
    file_gen = file_util.collect_files(node, recur=False)
    jobs = celery.chain(update_file_task.si(fn._id, file_util.get_file_content_url(fn)) for fn in file_gen)
    jobs.delay()
    logger.info('\n\n I must acknowledge the fact that update all has been called!')
