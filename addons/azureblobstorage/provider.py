# -*- coding: utf-8 -*-

from website.oauth.models import BasicAuthProviderMixin


class AzureBlobStorageProvider(BasicAuthProviderMixin):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'Azure Blob Storage'
    short_name = 'azureblobstorage'

    def __init__(self, account=None):
        super(AzureBlobStorageProvider, self).__init__()

        # provide an unauthenticated session by default
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )
