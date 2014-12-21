import os
import re

from waterbutler.core import metadata


class DropboxMetadata(metadata.BaseMetadata):

    def __init__(self, data, root):
        stripped = re.sub('^{}/?'.format(re.escape(root)), '', data['path'])
        assert stripped != data['path'], 'Root folder not present in path'
        data['path'] = stripped
        super().__init__(data)

    @property
    def provider(self):
        return 'dropbox'

    @property
    def kind(self):
        return 'folder' if self.raw['is_dir'] else 'file'

    @property
    def name(self):
        return os.path.split(self.raw['path'])[1]

    @property
    def path(self):
        return self.raw['path']

    @property
    def size(self):
        return self.raw['bytes']

    @property
    def modified(self):
        return self.raw['modified']


# TODO dates!
class DropboxRevision(metadata.BaseRevision):

    @property
    def provider(self):
        return 'dropbox'

    @property
    def size(self):
        return self.raw['bytes']

    @property
    def modified(self):
        return self.raw['modified']

    @property
    def revision(self):
        return self.raw['rev']

    @property
    def extra(self):
        return {
            'revisionNumber': self.raw['revision']
        }
