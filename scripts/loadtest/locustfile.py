#!/usr/bin/env python
# encoding: utf-8
"""Load testing for file upload, listing, and download with OSF Storage.
"""

import json
import random
import string
from io import StringIO

from locust import HttpLocust, TaskSet, task


HOST = 'http://localhost:5000/'
USERNAME = 'calici@cat.com'
PASSWORD = 'asdfasdf'
VERIFY = False

PROJECT_TITLE = 'load-test'
FILE_NAME = 'the-miracle.mp3'
FILE_SIZE = 1024
CONTENT_TYPE = 'text/plain'


def random_string(nchars):
    return ''.join([
        random.choice(string.lowercase)
        for _ in range(nchars)
    ])


def make_file_name(nchars):
    return random_string(nchars)


def make_file_like(nchars):
    sio = StringIO(random_string(nchars))
    return sio


class UserBehavior(TaskSet):

    def __init__(self, *args, **kwargs):
        super(UserBehavior, self).__init__(*args, **kwargs)
        self.node_id = None

    def login(self):
        self.client.post(
            'login/',
            {'username': USERNAME, 'password': PASSWORD},
            verify=VERIFY,
        )

    def create_project(self):
        resp = self.client.post(
            'api/v1/project/new/',
            data=json.dumps({'title': PROJECT_TITLE}),
            headers={'Content-Type': 'application/json'},
            verify=VERIFY,
        )
        node_url = resp.json()['projectUrl']
        self.node_id = node_url.strip('/').split('/')[-1]

    def on_start(self):
        self.login()
        self.create_project()
        self.upload_file(name=FILE_NAME)

    @task
    def upload_file(self, name=None):
        request_url = 'api/v1/project/{0}/osfstorage/files/'.format(self.node_id)
        resp = self.client.post(
            request_url,
            data=json.dumps({
                'name': name or make_file_name(16),
                'size': FILE_SIZE,
                'type': CONTENT_TYPE,
            }),
            headers={'Content-Type': 'application/json'},
            name='/api/v1/project/[nodeId]/osfstorage/files/',
        )
        upload_url = resp.json()
        self.client.put(
            upload_url,
            data=make_file_like(FILE_SIZE),
            headers={'Content-Type': CONTENT_TYPE},
            name='/files/',
        )

    @task
    def list_files(self):
        self.client.get(
            'api/v1/{0}/osfstorage/files/'.format(self.node_id),
            verify=VERIFY,
            name='/api/v1/project/[nodeId]/osfstorage/files/',
        )

    @task
    def download_file(self):
        self.client.get(
            'project/{0}/osfstorage/files/{1}/download/'.format(
                self.node_id, FILE_NAME,
            ),
            verify=VERIFY,
            name='/project/[nodeId]/osfstorage/files/[fileName]/download/',
        )


class WebsiteUser(HttpLocust):
    host = HOST
    task_set = UserBehavior
    min_wait = 5000
    max_wait = 10000
