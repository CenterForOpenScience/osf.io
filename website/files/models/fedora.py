from website.files.models.base import File, Folder, FileNode


__all__ = ('FedoraFile', 'FedoraFolder', 'FedoraFileNode')


class FedoraFileNode(FileNode):
    provider = 'fedora'


class FedoraFolder(FedoraFileNode, Folder):
    pass


class FedoraFile(FedoraFileNode, File):
    pass
