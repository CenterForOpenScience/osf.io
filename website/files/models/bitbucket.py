from website.files.models.base import File, Folder, FileNode


__all__ = ('BitbucketFile', 'BitbucketFolder', 'BitbucketFileNode')


class BitbucketFileNode(FileNode):
    provider = 'bitbucket'


class BitbucketFolder(BitbucketFileNode, Folder):
    pass


class BitbucketFile(BitbucketFileNode, File):
    version_identifier = 'commitSha'

    def touch(self, auth_header, revision=None, commitSha=None, branch=None, **kwargs):
        revision = revision or commitSha or branch
        return super(BitbucketFile, self).touch(auth_header, revision=revision, **kwargs)
