import httplib as http

from framework.auth import Auth
from framework.exceptions import HTTPError, PermissionsError
from website.addons.dataverse import serializer
from website.oauth.models import ExternalAccount


class DataverseProvider(object):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'Dataverse'
    short_name = 'dataverse'
    provider_name = 'dataverse'
    serializer = serializer.DataverseSerializer

    def __init__(self):
        super(DataverseProvider, self).__init__()

        # provide an unauthenticated session by default
        self.account = None

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )

    def add_user_auth(self, node_addon, user, external_account_id):

        external_account = ExternalAccount.load(external_account_id)

        if external_account not in user.external_accounts:
            raise HTTPError(http.FORBIDDEN)

        try:
            node_addon.set_auth(external_account, user)
        except PermissionsError:
            raise HTTPError(http.FORBIDDEN)

        result = self.serializer(
            node_settings=node_addon,
            user_settings=user.get_addon('dataverse'),
        ).serialized_node_settings
        return {'result': result}

    def remove_user_auth(self, node_addon, user):

        node_addon.deauthorize(Auth(user=user))
        node_addon.reload()
        result = self.serializer(
            node_settings=node_addon,
            user_settings=user.get_addon(self.provider_name),
        ).serialized_node_settings
        return {'result': result}
