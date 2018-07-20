class MockFolder(dict, object):

    def __init__(self):
        self.name = 'Fake Folder'
        self.json = {'id': 'Fake Key', 'parent_id': 'cba321', 'name': 'Fake Folder'}
        self['data'] = {'name': 'Fake Folder', 'key': 'Fake Key', 'parentCollection': False}
        self['library'] = {'type': 'personal', 'id': '34241'}
        self['name'] = 'Fake Folder'
        self['id'] = 'Fake Key'


class MockLibrary(dict, object):

    def __init__(self):
        self.name = 'Fake Library'
        self.json = {'id': 'Fake Library Key', 'parent_id': 'cba321'}
        self['data'] = {'name': 'Fake Library', 'key': 'Fake Key', 'id': '12345' }
        self['name'] = 'Fake Library'
        self['id'] = 'Fake Library Key'
