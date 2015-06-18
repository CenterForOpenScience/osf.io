from waterbutler.core import metadata


class BaseFigshareMetadata:

    @property
    def provider(self):
        return 'figshare'


class FigshareFileMetadata(BaseFigshareMetadata, metadata.BaseMetadata):

    def __init__(self, raw, parent, child):
        super().__init__(raw)
        self.parent = parent
        self.article_id = parent['article_id']
        self.child = child

    @property
    def kind(self):
        return 'file'

    @property
    def name(self):
        return self.raw['name']

    @property
    def path(self):
        if self.child:
            return '/{0}/{1}'.format(self.article_id, self.raw['id'])
        return '/{0}'.format(self.raw['id'])

    @property
    def materialized_path(self):
        if self.child:
            return '/{0}/{1}'.format(self.parent['title'], self.name)
        return '/{0}'.format(self.name)

    @property
    def size(self):
        return self.raw.get('size')

    @property
    def modified(self):
        return None

    @property
    def can_delete(self):
        """Files can be deleted if private or if containing fileset contains
        two or more files.
        """
        return (
            self.parent['status'].lower() == 'drafts' or
            len(self.parent.get('files', [])) > 1
        )

    @property
    def etag(self):
        return '{}::{}::{}'.format(self.parent['status'].lower(), self.article_id, self.raw['id'])

    @property
    def extra(self):
        return {
            'fileId': self.raw['id'],
            'articleId': self.article_id,
            'status': self.parent['status'].lower(),
            'downloadUrl': self.raw.get('download_url'),
            'canDelete': self.can_delete,
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
    def materialized_path(self):
        return '/{0}/'.format(self.name)

    @property
    def size(self):
        return None

    @property
    def modified(self):
        return None

    @property
    def etag(self):
        return '{}::{}::{}'.format(self.raw['status'].lower(), self.raw.get('doi'), self.raw.get('article_id'))

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
