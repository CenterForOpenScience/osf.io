from website.files.models.base import File, Folder, FileNode

__all__ = ('EvernoteFile', 'EvernoteFolder', 'EvernoteFileNode')

class EvernoteFileNode(FileNode):
    provider = 'evernote'


class EvernoteFolder(EvernoteFileNode, Folder):
    pass


class EvernoteFile(EvernoteFileNode, File):
    pass
