from website.files.models.base import File, Folder, FileNode


__all__ = ('DryadFile', 'DryadFolder', 'DryadFileNode')


class DryadFileNode(FileNode):
    provider = 'dryad'


class DryadFolder(DryadFileNode, Folder):
    pass


class DryadFile(DryadFileNode, File):
    pass
