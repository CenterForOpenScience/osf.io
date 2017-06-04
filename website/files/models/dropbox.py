from website.files.models.base import File, Folder
from website.files.models.ext import PathFollowingFileNode


__all__ = ('DropboxFile', 'DropboxFolder', 'DropboxFileNode')


class DropboxFileNode(PathFollowingFileNode):
    provider = 'dropbox'


class DropboxFolder(DropboxFileNode, Folder):
    pass


class DropboxFile(DropboxFileNode, File):
    pass
