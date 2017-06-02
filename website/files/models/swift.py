from website.files.models.base import File, Folder, FileNode

__all__ = ('SwiftFile', 'SwiftFolder', 'SwiftFileNode')


class SwiftFileNode(FileNode):
    provider = 'swift'


class SwiftFolder(SwiftFileNode, Folder):
    pass


class SwiftFile(SwiftFileNode, File):
    version_identifier = 'version'
