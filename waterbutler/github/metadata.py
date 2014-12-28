import os

from waterbutler.core import metadata


class BaseGitHubMetadata(metadata.BaseMetadata):

    def __init__(self, raw, folder=None):
        super().__init__(raw)
        self.folder = folder

    @property
    def provider(self):
        return 'github'

    @property
    def extra(self):
        return {
            'sha': self.raw['sha']
        }

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
        return None


class GitHubFolderTreeMetadata(BaseGitHubFolderMetadata):

    @property
    def name(self):
        return os.path.basename(self.raw['path'])


# TODO dates!
class GitHubRevision(BaseGitHubMetadata, metadata.BaseFileRevisionMetadata):

    @property
    def size(self):
        return None

    @property
    def modified(self):
        return self.raw['commit']['committer']['date']
