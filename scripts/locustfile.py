# -*- coding: utf-8 -*-

import random
from StringIO import StringIO

from locust import HttpLocust, TaskSet, task

USERNAME = 'jm.carp+locust@gmail.com'
PASSWORD = 'locust'
PROJECT_ID = '3vubz'
FILE_ID = 'fk6tb'
FILE_NCHARS = 1024
ROUTE = 'gitlab'


def gen_file_like(nchars=None, name=None):
    nchars = nchars or FILE_NCHARS
    name = name or str(random.randint(1000, 9999))
    sio = StringIO('l' * nchars)
    sio.name = name
    return sio


class UserBehavior(TaskSet):

    def on_start(self):
        self.login()

    def login(self):
        self.client.post(
            '/login/',
            {'username': USERNAME, 'password': PASSWORD}
        )

    @task
    def list_files(self):
        self.client.get('/api/v1/{0}/osffiles/'.format(PROJECT_ID))

    @task
    def download_file(self):
        self.client.get('/{0}/download/'.format(FILE_ID))

    @task
    def upload_file(self):
        self.client.post(
            '/api/v1/project/{0}/{1}/files/'.format(PROJECT_ID, ROUTE),
            files={'file': gen_file_like()}
        )


class WebsiteUser(HttpLocust):
    host = 'http://localhost:5000'
    task_set = UserBehavior
    min_wait = 5000
    max_wait = 10000

