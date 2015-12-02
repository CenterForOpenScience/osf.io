from website.files.models.base import File, Folder, FileNode


__all__ = ('OneDriveFile', 'OneDriveFolder', 'OneDriveFileNode')


class OneDriveFileNode(FileNode):
    provider = 'onedrive'


class OneDriveFolder(OneDriveFileNode, Folder):
    pass


class OneDriveFile(OneDriveFileNode, File):
    pass
