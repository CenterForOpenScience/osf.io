import logging

from framework.tasks import app
from framework.tasks.handlers import enqueue_task
from website.search import search

@app.task
def update_file_task(name, path, addon, index=None):
    logging.info('UPDATE FROM CELERY\n')
    search.update_file(name, path, addon, index)


@app.task
def delete_file_task(name, path, addon, index=None):
    logging.info('DELETE FROM CELERY\n')
    search.delete_file(name, path, addon, index)


@app.task
def update_all_files_task(node, index=None):
    logging.info('UPDATE ALL FROM CELERY\n')
    search.update_all_files(node, index)


@app.task
def delete_all_files_task(node, index=None):
    logging.info('DELETE ALL FROM CELERY\n')
    search.delete_all_files(node, index)
