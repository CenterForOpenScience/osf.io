from framework.tasks import app as celery_app

def get_task_by_id(task_id):
    return celery_app.AsyncResult(task_id)
