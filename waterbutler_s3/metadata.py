import os

from waterbutler.providers import core


class S3FileMetadata(core.BaseMetadata):

    @property
    def provider(self):
        return 's3'

    @property
    def kind(self):
        return 'file'

    @property
    def name(self):
        return os.path.split(self.raw.Key.text)[1]

    @property
    def path(self):
        return self.raw.Key.text

    @property
    def size(self):
        return self.raw.Size.text

    @property
    def modified(self):
        return self.raw.LastModified.text

    @property
    def extra(self):
        return {
            'md5': self.raw.ETag.text.replace('"', '')
        }


class S3FolderMetadata(core.BaseMetadata):

    @property
    def provider(self):
        return 's3'

    @property
    def kind(self):
        return 'folder'

    @property
    def name(self):
        return self.raw.Prefix.text.split('/')[-2]

    @property
    def path(self):
        return self.raw.Prefix.text

    @property
    def size(self):
        return None

    @property
    def modified(self):
        return None
