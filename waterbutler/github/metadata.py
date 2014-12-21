from waterbutler.core import metadata


class GithubMetadata(metadata.BaseMetadata):

    @property
    def provider(self):
        return 'github'

    @property
    def kind(self):
        return 'file' if self.raw['type'] == 'file' else 'folder'

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
    def extra(self):
        return {
            'sha': self.raw['sha']
        }


# TODO dates!
class GithubRevision(metadata.BaseRevision):

    @property
    def provider(self):
        return 'github'

    @property
    def size(self):
        return None

    @property
    def modified(self):
        return self.raw['commit']['committer']['date']

    @property
    def revision(self):
        return self.raw['sha']