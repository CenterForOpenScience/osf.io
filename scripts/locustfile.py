# -*- coding: utf-8 -*-

import random
from StringIO import StringIO

from locust import HttpLocust, TaskSet, task

HOST = 'https://96.126.111.139'
USERNAME = 'jm.carp+gitlab.test@gmail.com'
PASSWORD = 'gitlab'
READ_PROJECT_ID = '8hatz'
WRITE_PROJECT_ID = 'kqf6z'
FILE_ID = '3bz8x'
FILE_NCHARS = 1024
ROUTE = 'osffiles'
VERIFY = False


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
            {'username': USERNAME, 'password': PASSWORD},
            verify=VERIFY,
        )

    #@task
    #def list_files(self):
    #    self.client.get(
    #        '/api/v1/{0}/osffiles/grid/'.format(READ_PROJECT_ID),
    #        verify=VERIFY
    #    )

    #@task
    #def download_file(self):
    #    self.client.get(
    #        '/{0}/download/'.format(FILE_ID),
    #        verify=VERIFY,
    #    )

    @task
    def upload_file(self):
        self.client.post(
            '/api/v1/project/{0}/{1}/files/'.format(WRITE_PROJECT_ID, ROUTE),
            files={'file': gen_file_like()},
            verify=VERIFY,
        )


class WebsiteUser(HttpLocust):
    host = HOST
    task_set = UserBehavior
    min_wait = 5000
    max_wait = 10000

