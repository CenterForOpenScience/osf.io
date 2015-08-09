import logging
import requests

from framework.tasks import app
from website import settings
from website.search import search
from website.addons.osfstorage import model
from website.app import init_addons, do_set_backends

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
    return search.delete_file_from_path(file_path, file_parent_id=parent_id, index=index)


@app.task
def update_all_files_task(node, index=None):
    search.update_all_files(node, index)


@app.task
def delete_all_files_task(node, index=None):
    search.delete_all_files(node, index)
