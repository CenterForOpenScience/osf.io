# -*- coding: utf-8 -*-

from osf.models.external import BasicAuthProviderMixin


class SwiftProvider(BasicAuthProviderMixin):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'Swift'
    short_name = 'swift'

    def __init__(self, account=None, auth_url=None, tenant_name=None,
                 username=None, password=None):
        if username:
            username = username.lower()
        return super(SwiftProvider, self).__init__(account=account,
                                                   host='{}\t{}'.format(auth_url, tenant_name),
                                                   username=username,
                                                   password=password)

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )

    @property
    def auth_url(self):
        if '\t' in self.host:
            return self.host.split('\t')[0]
        else:
            return None

    @property
    def tenant_name(self):
        if '\t' in self.host:
            return self.host.split('\t')[1]
        else:
            return None
