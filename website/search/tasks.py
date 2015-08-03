import logging

from framework.tasks import app
from framework.tasks import handlers
from website.search import search



# @handlers.queued_task
@app.task
def update_file_task(file_node, index=None):
    logging.info('UPDATE FROM CELERY\n')
    search.update_file(file_node, index)


# @handlers.queued_task
@app.task
def delete_file_task(file_node, index=None):
    logging.info('DELETE FROM CELERY\n')
    search.delete_file(file_node, index)


# @handlers.queued_task
@app.task
def update_all_files_task(node, index=None):
    logging.info('UPDATE ALL FROM CELERY\n')
    search.update_all_files(node, index)


# @handlers.queued_task
@app.task
def delete_all_files_task(node, index=None):
    logging.info('DELETE ALL FROM CELERY\n')
    search.delete_all_files(node, index)
