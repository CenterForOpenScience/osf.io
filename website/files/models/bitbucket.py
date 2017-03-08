from website.files.models.base import File, Folder, FileNode


__all__ = ('BitbucketFile', 'BitbucketFolder', 'BitbucketFileNode')


class BitbucketFileNode(FileNode):
    provider = 'bitbucket'


class BitbucketFolder(BitbucketFileNode, Folder):
    pass


class BitbucketFile(BitbucketFileNode, File):
    version_identifier = 'ref'

    def touch(self, auth_header, revision=None, ref=None, branch=None, **kwargs):
        revision = revision or ref or branch
        return super(BitbucketFile, self).touch(auth_header, revision=revision, **kwargs)
