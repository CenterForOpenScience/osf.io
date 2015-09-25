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
    init_addons(settings, routes=False)
    do_set_backends(settings)

    file_node = model.OsfStorageFileNode.load(file_node_id)
    content = requests.get(file_url).content
    return search.update_file(file_node, content, index)
    # return search.update_file_given_content(file_node, content, index)


@app.task
def delete_file_task(file_node_id, parent_id, index=None):
    from website.addons.osfstorage.model import OsfStorageFileNode
    init_addons(settings, routes=False)
    do_set_backends(settings)
    search.delete_file_given_path(file_node_id, parent_id, index=index)
    # file_node = OsfStorageFileNode.load(file_node_id)
    # return search.delete_file(file_node, parent_id=parent_id, index=index)


@app.task
def move_file_task(file_node_id, old_parent_id, new_parent_id, file_url, index=None):
    from website.addons.osfstorage.model import OsfStorageFileNode
    init_addons(settings, routes=False)
    do_set_backends(settings)
    file_node = OsfStorageFileNode.load(file_node_id)
    content = requests.get(file_url).content
    return search.move_file(file_node, old_parent_id, new_parent_id, content=content)


@app.task
def copy_file_task(file_node_id, new_file_node_id, old_parent_id, new_parent_id, file_url, index=None):
    from website.addons.osfstorage.model import OsfStorageFileNode
    init_addons(settings, routes=False)
    do_set_backends(settings)
    file_node = OsfStorageFileNode.load(file_node_id)
    content = requests.get(file_url).content
    return search.copy_file(file_node, new_file_node_id, old_parent_id, new_parent_id, content=content)


def update_all_files_task(node):
    file_gen = file_util.collect_files(node, recur=False)
    jobs = celery.chain(update_file_task.si(fn._id, file_util.get_file_content_url(fn)) for fn in file_gen)
    jobs.delay()
