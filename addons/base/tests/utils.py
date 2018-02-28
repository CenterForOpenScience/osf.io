class MockFolder(dict, object):

    def __init__(self):
        self.name = 'Fake Folder'
        self.json = {'id': 'Fake Key', 'parent_id': 'cba321'}
        self['data'] = {'name': 'Fake Folder', 'key': 'Fake Key'}
        self['name'] = 'Fake Folder'
        self['id'] = 'Fake Key'


class MockLibrary(dict, object):

    def __init__(self):
        self.name = 'Fake Library'
        self.json = {'id': 'Fake Library Key', 'parent_id': 'cba321'}
        self['data'] = {'name': 'Fake Library', 'key': 'Fake Key'}
        self['name'] = 'Fake Library'
        self['id'] = 'Fake Library Key'
