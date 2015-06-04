from framework.tasks import app

from website.project.decorators import must_be_valid_project

@must_be_valid_project
def archiver_debug(node, *args, **kwargs):
    task = app.AsyncResult(node.archive_task_id)
    task_meta = {}
    try:
        task_meta = {
            'id': task.task_id,
            'state': task.state,
            'result': str(task.result),
            'traceback': str(task.traceback),
        }
    except:
        pass
    return {
        'archiving': node.archiving,
        'archived_providers': node.archived_providers,
        'archive_status': node.archive_status,
        'task': task_meta,
    }
