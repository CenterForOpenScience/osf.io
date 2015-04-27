import logging
import requests
from celery.contrib import rdb

from framework.tasks import app

logger = logging.getLogger(__name__)


@app.task(bind=True)
def get_static_snapshot(self, url, cookie):
    params = {
        'url': url
    }
    response = requests.get('http://localhost:3000', params=params, cookies=cookie)
    content = {}
    if response.status_code == 200:
        rdb.set_trace()
        self.update_state(state='SUCCESS',
                          meta={'content': content})
    else:
        self.update_state(state='PENDING', meta={'content': content})
    return {'content': content}
