import logging
import requests

from framework.tasks import app

logger = logging.getLogger(__name__)


@app.task(bind=True)
def get_static_snapshot(self, url, path):
    params = {
        'url': url,
    }
    content = {}
    print " In celery task"
    print path
    response = requests.get('http://localhost:3000', params=params)
    if response.status_code == 200:
        print " in success", '****************'
        content = response.text
        self.update_state(state='SUCCESS')
    else:
        print " in pending", '*********************'
        self.update_state(state='PENDING')

    return {'content': content,
            'path': path}
