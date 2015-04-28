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
    print " Check if debugging works"
    content = {}
    response = requests.get('http://localhost:3000', params=params, cookies=cookie)
    if response.status_code == 200:
        print " in success", '****************'
        content = response.text
        self.update_state(state='SUCCESS',
                          meta={'content': response.text})
    else:
        print " in pending", '*********************'
        self.update_state(state='PENDING', meta={'content': content})
    return {'content': content}
