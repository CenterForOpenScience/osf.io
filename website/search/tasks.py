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
    logger.info('\n\nI do declare, Update File has been called\n')

    init_addons(settings)
    do_set_backends(settings)
    file_node = model.OsfStorageFileNode.load(file_node_id)

    content = requests.get(file_url).content

    return search.update_file_given_content(file_node, content, index)


@app.task
def delete_file_task(file_node, index=None):
    search.delete_file(file_node, index)


@app.task
def update_all_files_task(node, index=None):
    search.update_all_files(node, index)


@app.task
def delete_all_files_task(node, index=None):
    search.delete_all_files(node, index)
