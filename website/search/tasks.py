import logging

from framework.tasks import app
from framework.tasks.handlers import enqueue_task
from website.search import search


def _enqueue(func):
    return lambda *args, **kwargs: enqueue_task(func.s(*args, **kwargs))

@app.task
def update_file_task(file_node, index=None):
    logging.info('UPDATE FROM CELERY\n')
    search.update_file(file_node, index)


@app.task
def delete_file_task(file_node, index=None):
    logging.info('DELETE FROM CELERY\n')
    search.delete_file(file_node, index)


@app.task
def update_all_files_task(node, index=None):
    logging.info('UPDATE ALL FROM CELERY\n')
    search.update_all_files(node, index)


@app.task
def delete_all_files_task(node, index=None):
    logging.info('DELETE ALL FROM CELERY\n')
    search.delete_all_files(node, index)


queue_update_file = _enqueue(update_file_task)
queue_delete_file = _enqueue(delete_file_task)
queue_update_all_files = _enqueue(update_all_files_task)
queue_delete_all_files = _enqueue(delete_all_files_task)
