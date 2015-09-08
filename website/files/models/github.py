from website.files.models.base import File, Folder, FileNode


__all__ = ('GithubFile', 'GithubFolder', 'GithubFileNode')


class GithubFileNode(FileNode):
    provider = 'github'


class GithubFolder(GithubFileNode, Folder):
    pass


class GithubFile(GithubFileNode, File):
    version_identifier = 'ref'
