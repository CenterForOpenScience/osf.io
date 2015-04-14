import os

from waterbutler.core import metadata


class BaseBoxMetadata(metadata.BaseMetadata):

    def __init__(self, raw, folder):
        super().__init__(raw)
        self.folder = folder

    @property
    def provider(self):
        return 'box'

    @property
    def full_path(self):
        if 'path_collection' not in self.raw:
            return None

        path = []
        if self.raw['id'] != self.folder:
            for entry in reversed(self.raw['path_collection']['entries']):
                if self.folder == entry['id']:
                    break
                path.append(entry['name'])

        return '/' + os.path.join('/'.join(reversed(path)), self.name)

    @property
    def extra(self):
        return {
            'fullPath': self.full_path
        }


class BoxFolderMetadata(BaseBoxMetadata, metadata.BaseFolderMetadata):

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        return '/{}/'.format(self.raw['id'])

    @property
    def full_path(self):
        path = super().full_path
        if path is None:
            return None
        return path + '/'


class BoxFileMetadata(BaseBoxMetadata, metadata.BaseFileMetadata):

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        return '/{0}/{1}'.format(self.raw['id'], self.raw['name'])

    @property
    def size(self):
        return self.raw.get('size')

    @property
    def modified(self):
        return self.raw.get('modified_at')

    @property
    def content_type(self):
        return None

    @property
    def extra(self):
        return {
            'etag': self.raw.get('etag'),
            'fullPath': self.full_path
        }

    @property
    def materialized_path(self):
        if 'path_collection' not in self.raw:
            return None

        path = []
        for entry in reversed(self.raw['path_collection']['entries']):
            if self.folder == entry['id']:
                break
            path.append(entry['name'])

        return '/' + os.path.join('/'.join(reversed(path)), self.name)


class BoxRevision(metadata.BaseFileRevisionMetadata):

    @property
    def version(self):
        try:
            return self.raw['id']
        except KeyError:
            return self.raw['path'].split('/')[1]

    @property
    def version_identifier(self):
        return 'revision'

    @property
    def path(self):
        try:
            return '/{0}/{1}'.format(self.raw['id'], self.raw['name'])
        except KeyError:
            return self.raw.get('path')

    @property
    def modified(self):
        try:
            return self.raw['modified_at']
        except KeyError:
            return self.raw.get('modified')
