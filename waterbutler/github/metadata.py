from waterbutler.core import metadata

class BaseGithubMetadata:

    @property
    def provider(self):
        return 'github'


class GithubFileMetadata(BaseGithubMetadata, metadata.BaseFileMetadata):

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        return self.raw['path']

    @property
    def size(self):
        return self.raw['size']

    @property
    def modified(self):
        return None

    @property
    def content_type(self):
        return None

    @property
    def extra(self):
        return {
            'sha': self.raw['sha']
        }


class GithubFolderMetadata(BaseGithubMetadata, metadata.BaseFolderMetadata):

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        return self.raw['path']


# TODO dates!
class GithubRevision(BaseGithubMetadata, metadata.BaseFileRevisionMetadata):

    @property
    def size(self):
        return None

    @property
    def modified(self):
        return self.raw['commit']['committer']['date']

    @property
    def revision(self):
        return self.raw['sha']
