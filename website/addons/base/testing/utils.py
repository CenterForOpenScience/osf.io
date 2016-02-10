# -*- coding: utf-8 -*-
class MockFolder(dict, object):

    def __init__(self):
        self.name = 'Fake Folder'
        self.json = {'id': 'Fake Key', 'parent_id': 'cba321'}
        self['data'] = {'name': 'Fake Folder', 'key': 'Fake Key'}
        self['name'] = 'Fake Folder'
        self['id'] = 'Fake Key'
