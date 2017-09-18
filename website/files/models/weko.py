from website.files.models.base import File, Folder, FileNode

__all__ = ('WEKOFile', 'WEKOFolder', 'WEKOFileNode')


class WEKOFileNode(FileNode):
    provider = 'weko'


class WEKOFolder(WEKOFileNode, Folder):
    pass


class WEKOFile(WEKOFileNode, File):
    pass
