from website.files.models.base import File, Folder, FileNode

__all__ = ('DmptoolFile', 'DmptoolFolder', 'DmptoolFileNode')

class DmptoolFileNode(FileNode):
    provider = 'dmptool'


class DmptoolFolder(DmptoolFileNode, Folder):
    pass


class DmptoolFile(DmptoolFileNode, File):
    pass
