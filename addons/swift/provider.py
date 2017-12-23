# -*- coding: utf-8 -*-

from osf.models.external import BasicAuthProviderMixin


def to_auth_desc(auth_version, auth_url, user_domain_name, tenant_name,
                 project_domain_name):
    if auth_version == '2':
        return '{}\t{}'.format(auth_url, tenant_name)
    elif auth_version == '3':
        return 'v3:{}\t{}\t{}\t{}'.format(auth_url, tenant_name,
                                          project_domain_name, user_domain_name)
    else:
        raise ValueError('Unexpected identity version: {}'.format(auth_version))

def parse_auth_desc(host):
    if host.startswith('v3:'):
        t = host[3:].split('\t')
        return ('3', t[0], t[1], t[2], t[3])
    elif '\t' in host:
        t = host.split('\t')
        return ('2', t[0], t[1], None, None)
    else:
        raise ValueError('Unexpected auth_desc: {}'.format(host))



class SwiftProvider(BasicAuthProviderMixin):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'OpenStack Swift'
    short_name = 'swift'

    def __init__(self, account=None, auth_version=None, auth_url=None,
                 tenant_name=None, project_domain_name=None,
                 username=None, user_domain_name=None,
                 password=None):
        if username:
            username = username.lower()
        if auth_version is not None:
            desc = to_auth_desc(auth_version, auth_url, user_domain_name,
                                tenant_name, project_domain_name)
        else:
            desc = None
        return super(SwiftProvider, self).__init__(account=account,
                                                   host=desc,
                                                   username=username,
                                                   password=password)

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )

    @property
    def auth_version(self):
        version, auth_url, tenant_name, project_domain_name, user_domain_name = parse_auth_desc(self.host)
        return version

    @property
    def auth_url(self):
        version, auth_url, tenant_name, project_domain_name, user_domain_name = parse_auth_desc(self.host)
        return auth_url

    @property
    def tenant_name(self):
        version, auth_url, tenant_name, project_domain_name, user_domain_name = parse_auth_desc(self.host)
        return tenant_name

    @property
    def project_domain_name(self):
        version, auth_url, tenant_name, project_domain_name, user_domain_name = parse_auth_desc(self.host)
        return project_domain_name

    @property
    def user_domain_name(self):
        version, auth_url, tenant_name, project_domain_name, user_domain_name = parse_auth_desc(self.host)
        return user_domain_name
