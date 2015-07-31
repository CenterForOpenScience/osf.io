from website.files.models.base import File, Folder, FileNode


class BoxFileNode(FileNode):
    provider = 'box'


class BoxFolder(BoxFileNode, Folder):
    pass


class BoxFile(BoxFileNode, File):
    pass
