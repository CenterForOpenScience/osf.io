import os

from waterbutler.core import metadata


class S3Metadata(metadata.BaseMetadata):

    @property
    def provider(self):
        return 's3'

    @property
    def name(self):
        return os.path.split(self.path)[1]


class S3FileMetadataHeaders(metadata.BaseFileMetadata, S3Metadata):

    def __init__(self, path, headers):
        self._path = path
        super().__init__(headers)

    @property
    def path(self):
        return self._path

    @property
    def size(self):
        return self.raw['Content-Length']

    @property
    def content_type(self):
        return self.raw['Content-Type']

    @property
    def modified(self):
        return self.raw['Last-Modified']

    @property
    def extra(self):
        return {
            'md5': self.raw['ETag'].replace('"', '')
        }


class S3FileMetadata(metadata.BaseFileMetadata, S3Metadata):

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
    def content_type(self):
        return None  # TODO

    @property
    def extra(self):
        return {
            'md5': self.raw.ETag.text.replace('"', '')
        }


class S3FolderKeyMetadata(metadata.BaseFolderMetadata, S3Metadata):

    @property
    def name(self):
        return self.raw.Key.text.split('/')[-2]

    @property
    def path(self):
        return self.raw.Key.text


class S3FolderMetadata(metadata.BaseFolderMetadata, S3Metadata):

    @property
    def name(self):
        return self.raw.Prefix.text.split('/')[-2]

    @property
    def path(self):
        return self.raw.Prefix.text


# TODO dates!
class S3Revision(metadata.BaseFileRevisionMetadata, S3Metadata):

    def __init__(self, path, raw):
        self._path = path
        super().__init__(raw)

    @property
    def path(self):
        return self._path

    @property
    def content_type(self):
        return None  # TODO

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
