from website.files.models.base import File, Folder, FileNode

__all__ = ('S3File', 'S3Folder', 'S3FileNode')


class S3FileNode(FileNode):
    provider = 's3'


class S3Folder(S3FileNode, Folder):
    pass


class S3File(S3FileNode, File):
    def touch(self, version=None, **kwargs):
        return super(S3File, self).touch(version=version, **kwargs)
