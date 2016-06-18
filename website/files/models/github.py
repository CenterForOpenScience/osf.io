from website.files.models.base import File, Folder, FileNode


__all__ = ('GithubFile', 'GithubFolder', 'GithubFileNode')


class GithubFileNode(FileNode):
    provider = 'github'


class GithubFolder(GithubFileNode, Folder):
    pass


class GithubFile(GithubFileNode, File):
    version_identifier = 'ref'

    def touch(self, auth_header, revision=None, ref=None, branch=None, **kwargs):
        revision = revision or ref or branch
        return super(GithubFile, self).touch(auth_header, revision=revision, **kwargs)
