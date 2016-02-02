# -*- coding: utf-8 -*-

class MockNode(object):

    addon = None
    addon_name = None

    def __init__(self, name=None):
        self.addon_name = name

    @property
    def is_deleted(self):
        return False

    @property
    def is_public(self):
        return True

    def get_addon(self, name):
        if name == self.addon_name:
            return self.addon
        return None

class MockFolder(dict, object):

    def __init__(self):
        self.name = 'Fake Folder'
        self.json = {'id': 'Fake Key', 'parent_id': 'cba321'}
        self['data'] = {'name': 'Fake Folder', 'key': 'Fake Key'}
        self['name'] = 'Fake Folder'
        self['id'] = 'Fake Key'
