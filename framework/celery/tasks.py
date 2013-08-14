from __future__ import absolute_import

from framework.celery.celery import celery
from celery.utils.log import get_task_logger

@celery.task
def error_handler(task_id, task_name):
    """logs detailed message about tasks that raise exceptions

    :param task_id: TaskID of the failed task
    :param task_name: name of task that failed
    """

    # get the current logger
    logger = get_task_logger(__name__)

    # query the broker for the AsyncResult
    result = celery.AsyncResult(task_id)
    excep = result.get(propagate=False)
    # log detailed error mesage in error log
    logger.error('#####FAILURE LOG BEGIN#####\nTask %r raised exception: %r\n\%r\n#####FAILURE LOG STOP#####' % (task_name, excep, result.traceback))
    #print('#####FAILURE LOG BEGIN#####\nTask %r raised exception: %r\n\%r\n#####FAILURE LOG STOP#####' % (task_name, excep, result.traceback))
