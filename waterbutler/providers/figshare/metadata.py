from waterbutler.core import metadata


class BaseFigshareMetadata:

    @property
    def provider(self):
        return 'figshare'


class FigshareFileMetadata(BaseFigshareMetadata, metadata.BaseMetadata):

    def __init__(self, raw, article_id):
        super().__init__(raw)
        self.article_id = article_id

    @property
    def kind(self):
        return 'file'

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        if self.article_id:
            return '/{0}/{1}'.format(self.article_id, self.raw['id'])
        return '/{0}'.format(self.raw['id'])

    @property
    def size(self):
        return self.raw.get('size')

    @property
    def modified(self):
        return None

    @property
    def extra(self):
        return {
            'fileId': self.raw['id'],
            'articleId': self.article_id,
            'downloadUrl': self.raw.get('download_url'),
        }


class FigshareArticleMetadata(BaseFigshareMetadata, metadata.BaseMetadata):

    @property
    def kind(self):
        return 'folder'

    @property
    def name(self):
        return self.raw['title']

    @property
    def path(self):
        return '/{0}/'.format(self.raw.get('article_id'))

    @property
    def size(self):
        return None

    @property
    def modified(self):
        return None

    @property
    def extra(self):
        return {
            'id': self.raw.get('article_id'),
            'doi': self.raw.get('doi'),
            'status': self.raw['status'].lower(),
        }


class FigshareProjectMetadata(BaseFigshareMetadata, metadata.BaseMetadata):

    @property
    def kind(self):
        return 'folder'

    @property
    def name(self):
        return self.raw['title']

    @property
    def path(self):
        return '{0}/'.format(self.name)
