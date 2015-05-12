import os
import logging

from framework.render.tasks import ensure_path
from website.static_snapshot import tasks
from website import settings

logger = logging.getLogger(__name__)


def get_static_snapshot(cache):
    """
    View function to handle the url call made by google bot crawler
    """
    if settings.USE_CELERY:

        response = {}
        task_id = cache.get('task_id')
        task = tasks.get_static_snapshot.AsyncResult(task_id)
        if task.id:

            if task.state == 'PENDING':
                logger.debug('Waiting for response from Phantom Server')

            elif task.state == 'SUCCESS':
                logger.debug('Static snapshot received. Caching the response in website/seocache')
                path = task.result['path']
                ensure_path(path)
                current_page = cache.get('current_page')
                file_name = os.path.join(path, current_page) + '.html'
                file_content = task.result['content'].encode('utf-8')
                with open(file_name, 'wb') as fp:
                    fp.write(file_content)
                cache.clear()
                response = {'content': task.result['content']}
            else:
                logger.warn('Invalid Celery task')

        elif cache.get('cached_content'):
            logger.debug('Cached Already')
            response = {'content': cache.get('cached_content')}
            cache.clear()

        else:
            logger.warn('No celery task id found')

        return response

    else:
        logger.warn("Is Celery turned ON?")
        return None
