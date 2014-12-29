import os

from waterbutler.core import metadata


class OsfStorageMetadata(metadata.BaseMetadata):

    def __init__(self, raw, path):
        super().__init__(raw)
        self._path = path

    @property
    def provider(self):
        return 'osfstorage'

    @property
    def kind(self):
        return self.raw['kind']

    @property
    def name(self):
        return os.path.split(self.path)[1]

    @property
    def path(self):
        return self._path

    @property
    def modified(self):
        return self.raw['modified']

    @property
    def size(self):
        return self.raw.get('size')

    @property
    def extra(self):
        return {}
