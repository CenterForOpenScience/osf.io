# -*- coding: utf-8 -*-
import mock
from contextlib import contextmanager

from modularodm import storage

from framework.mongo import set_up_storage

from website.addons.base.testing import AddonTestCase
from website.addons.dropbox import MODELS

from json import dumps

def init_storage():
    set_up_storage(MODELS, storage_class=storage.MongoStorage)

    
mock_responses = {
    'folders': [
        {
            "id": "4901a8f5-9840-49bf-8a17-bdb3d5900417",
            "name": "subfolder",
            "created": "2015-02-13T20:34:42.000Z",
            "modified": "2015-02-13T20:34:44.000Z"
        },
        {
            "id": "a6b12ebf-bd07-4f4e-ad73-f9704555f032",
            "name": "subfolder2",
            "created": "2015-02-13T20:34:42.000Z",
            "modified": "2015-02-13T20:34:44.000Z",
            "parent_id": "4901a8f5-9840-49bf-8a17-bdb3d5900417"
        },
        {
            "id": "e843da05-8818-47c2-8c37-41eebfc4fe3f",
            "name": "subfolder3",
            "created": "2015-02-17T15:27:13.000Z",
            "modified": "2015-02-17T15:27:13.000Z",
            "parent_id": "a6b12ebf-bd07-4f4e-ad73-f9704555f032"
        }
    ],    
}

mock_responses = {k:dumps(v) for k,v in mock_responses.iteritems()}
