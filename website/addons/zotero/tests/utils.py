# -*- coding: utf-8 -*-
import mock
from contextlib import contextmanager

from modularodm import storage

from framework.mongo import set_up_storage

from website.addons.base.testing import AddonTestCase
from website.addons.zotero import MODELS

from json import dumps as dump_json
from faker import Faker

fake = Faker()

class MockZotero(object):

    def __init__(self):
        self._folders = [
            {
                'data': {
                    "key": "4901a8f5-9840-49bf-8a17-bdb3d5900417",
                    "name": "subfolder",
                },
            },
            {
                'data': {
                    "key": "a6b12ebf-bd07-4f4e-ad73-f9704555f032",
                    "name": "subfolder2",
                    "parentCollection": "4901a8f5-9840-49bf-8a17-bdb3d5900417",
                },
            },
            {
                'data': {
                    "key": "e843da05-8818-47c2-8c37-41eebfc4fe3f",
                    "name": "subfolder3",
                    "parentCollection": "a6b12ebf-bd07-4f4e-ad73-f9704555f032",
                },
            },
        ]
        self._documents = []
        for i in range(150):
            doc = {
                'id': fake.ean(),
                'title': fake.sentence(),
                'type': 'journal',
                'authors': [
                    {
                        'first_name': fake.first_name(),
                        'last_name': fake.last_name(),
                    } for i in range(4)
                ],
                'year': fake.year(),
                'source': fake.company(),
                'identifiers': {},
                'created': fake.date() + 'T' + fake.time() + 'Z',
                'profile_id': fake.ean(),
                'last_modified': fake.date() + 'T' + fake.time() + 'Z',
                'abstract': ' '.join(fake.sentences())
            }
            self._documents.append(doc)

    def folders(self):
        return dump_json(self._folders)

    def documents(self, page=1):
        start = (page - 1) * 100
        stop = (page * 100)
        return dump_json(self._documents[start:stop])
