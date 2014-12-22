import os

from waterbutler.core import metadata


class S3FileMetadata(metadata.BaseMetadata):

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


class S3FolderMetadata(metadata.BaseMetadata):

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


# TODO dates!
class S3Revision(metadata.BaseRevision):

    @property
    def provider(self):
        return 's3'

    @property
    def size(self):
        return int(self.raw.Size.text)

    @property
    def revision(self):
        return self.raw.VersionId.text

    @property
    def modified(self):
        return self.raw.LastModified.text

    @property
    def extra(self):
        return {
            'md5': self.raw.ETag.text.replace('"', '')
        }
