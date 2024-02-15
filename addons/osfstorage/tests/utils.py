#!/usr/bin/env python3

from tests.base import OsfTestCase
from osf_tests.factories import ProjectFactory
from addons.osfstorage import settings as storage_settings

import collections

from framework.auth import Auth


identity = lambda value: value
class Delta:
    def __init__(self, getter, checker=None):
        self.getter = getter
        self.checker = checker or identity


class AssertDeltas:

    def __init__(self, *deltas):
        self.deltas = deltas
        self.original = []

    def __enter__(self):
        self.original = [delta.getter() for delta in self.deltas]

    def __exit__(self, exc_type, exc_value, exc_tb):
        for idx, delta in enumerate(self.deltas):
            final = delta.getter()
            assert delta.checker(self.original[idx]) == final


class StorageTestCase(OsfTestCase):

    def setUp(self):
        super().setUp()

        self.project = ProjectFactory()
        self.node = self.project
        self.user = self.project.creator
        self.node_settings = self.project.get_addon('osfstorage')
        self.auth_obj = Auth(user=self.project.creator)

        # Refresh records from database; necessary for comparing dates
        self.project.reload()
        self.user.reload()


def recursively_create_file(settings, path):
    path = path.split('/')
    final = path.pop(-1)
    current = settings.get_root()
    for subpath in path:
        current = current.append_folder(subpath)
    return current.append_file(final)


def recursively_create_folder(settings, path):
    path = path.split('/')
    final = path.pop(-1)
    current = settings.root_node
    for subpath in path:
        current = current.append_folder(subpath)
    return current.append_file(final)


def make_payload(user, name, **kwargs):
    payload = {
        'user': user._id,
        'name': name,
        'hashes': {'base64': '=='},
        'worker': {
            'uname': 'testmachine'
        },
        'settings': {
            'provider': 'filesystem',
            storage_settings.WATERBUTLER_RESOURCE: 'blah',
        },
        'metadata': {
            'size': 123,
            'name': 'file',
            'provider': 'filesystem',
            'modified': 'Mon, 16 Feb 2015 18:45:34 GMT'
        },
    }
    payload.update(kwargs)
    return payload
