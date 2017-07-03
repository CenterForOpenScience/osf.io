from website.files.models.base import File, Folder, FileNode


__all__ = ('GitLabFile', 'GitLabFolder', 'GitLabFileNode')


class GitLabFileNode(FileNode):
    provider = 'gitlab'


class GitLabFolder(GitLabFileNode, Folder):
    pass


class GitLabFile(GitLabFileNode, File):
    version_identifier = 'ref'

    def touch(self, auth_header, revision=None, ref=None, branch=None, **kwargs):
        revision = revision or ref or branch
        return super(GitLabFile, self).touch(auth_header, revision=revision, **kwargs)
