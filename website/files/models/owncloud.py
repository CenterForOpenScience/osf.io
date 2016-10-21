from website.files.models.base import File, Folder, FileNode


__all__ = ('OwncloudFile', 'OwncloudFolder', 'OwncloudFileNode')


class OwncloudFileNode(FileNode):
    provider = 'owncloud'


class OwncloudFolder(OwncloudFileNode, Folder):
    pass


class OwncloudFile(OwncloudFileNode, File):
    pass
