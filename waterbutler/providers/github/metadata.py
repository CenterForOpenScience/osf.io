import os

from waterbutler.core import metadata


class BaseGitHubMetadata(metadata.BaseMetadata):

    def __init__(self, raw, folder=None, **kwargs):
        super().__init__(raw)
        self.folder = folder
        self.extras = kwargs

    @property
    def provider(self):
        return 'github'

    @property
    def extra(self):
        ret = {
            'fileSha': self.raw['sha']
        }
        ret.update(self.extras)
        return ret

    def build_path(self, path):
        if self.folder:
            path = os.path.join(self.folder, path.lstrip('/'))
        return super().build_path(path)


class BaseGitHubFileMetadata(BaseGitHubMetadata, metadata.BaseFileMetadata):

    @property
    def path(self):
        return self.build_path(self.raw['path'])

    @property
    def modified(self):
        return None

    @property
    def content_type(self):
        return None


class BaseGitHubFolderMetadata(BaseGitHubMetadata, metadata.BaseFolderMetadata):

    @property
    def path(self):
        return self.build_path(self.raw['path'])


class GitHubFileContentMetadata(BaseGitHubFileMetadata):

    @property
    def name(self):
        return self.raw['name']

    @property
    def size(self):
        return self.raw['size']


class GitHubFolderContentMetadata(BaseGitHubFolderMetadata):

    @property
    def name(self):
        return self.raw['name']


class GitHubFileTreeMetadata(BaseGitHubFileMetadata):

    @property
    def name(self):
        return os.path.basename(self.raw['path'])

    @property
    def size(self):
        return self.raw['size']


class GitHubFolderTreeMetadata(BaseGitHubFolderMetadata):

    @property
    def name(self):
        return os.path.basename(self.raw['path'])


# TODO dates!
class GitHubRevision(metadata.BaseFileRevisionMetadata):

    @property
    def version_identifier(self):
        return 'ref'

    @property
    def modified(self):
        return self.raw['commit']['committer']['date']

    @property
    def version(self):
        return self.raw['sha']

    @property
    def extra(self):
        return {
            'user': {
                'name': self.raw['commit']['committer']['name']
            }
        }
