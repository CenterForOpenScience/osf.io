#!/usr/bin/env python
# encoding: utf-8

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

import collections

from framework.auth import Auth


Delta = collections.namedtuple('Delta', ['getter', 'checker'])


class AssertDeltas(object):

    def __init__(self, deltas):
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
        super(StorageTestCase, self).setUp()

        self.project = ProjectFactory()
        self.user = self.project.creator
        self.node_settings = self.project.get_addon('osfstorage')
        self.auth_obj = Auth(user=self.project.creator)

        # Refresh records from database; necessary for comparing dates
        self.project.reload()
        self.user.reload()
