from website.addons.base.serializer import OAuthAddonSerializer
from website.addons.dataverse import client
from website.addons.dataverse.settings import DEFAULT_HOSTS
from website.util import api_url_for, web_url_for


class DataverseSerializer(OAuthAddonSerializer):

    addon_short_name = 'dataverse'

    REQUIRED_URLS = []

    # Include host information with more informative labels / formatting
    def serialize_account(self, external_account):
        ret = super(DataverseSerializer, self).serialize_account(external_account)
        host = external_account.oauth_key
        ret.update({
            'host': host,
            'host_url': 'https://{0}'.format(host),
        })

        return ret

    @property
    def credentials_owner(self):
        return self.node_settings.user_settings.owner

    @property
    def serialized_urls(self):
        external_account = self.node_settings.external_account
        ret = {
            'settings': web_url_for('user_addons'),  # TODO: Is this needed?
        }
        # Dataverse users do not currently have profile URLs
        if external_account and external_account.profile_url:
            ret['owner'] = external_account.profile_url

        addon_urls = self.addon_serialized_urls
        # Make sure developer returns set of needed urls
        for url in self.REQUIRED_URLS:
            assert url in addon_urls, "addon_serilized_urls must include key '{0}'".format(url)
        ret.update(addon_urls)
        return ret

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        external_account = self.node_settings.external_account
        host = external_account.oauth_key if external_account else ''

        return {
            'create': api_url_for('dataverse_add_user_account'),
            'set': node.api_url_for('dataverse_set_config'),
            'importAuth': node.api_url_for('dataverse_import_auth'),
            'deauthorize': node.api_url_for('dataverse_deauthorize_node'),
            'getDatasets': node.api_url_for('dataverse_get_datasets'),
            'datasetPrefix': 'http://dx.doi.org/',
            'dataversePrefix': 'http://{0}/dataverse/'.format(host),
            'accounts': api_url_for('dataverse_account_list'),
        }

    @property
    def serialized_node_settings(self):
        result = super(DataverseSerializer, self).serialized_node_settings
        result['hosts'] = DEFAULT_HOSTS

        # Update with Dataverse specific fields
        if self.node_settings.has_auth:
            external_account = self.node_settings.external_account
            dataverse_host = external_account.oauth_key

            connection = client.connect_from_settings(self.node_settings)
            dataverses = client.get_dataverses(connection)
            result.update({
                'dataverseHost': dataverse_host,
                'connected': connection is not None,
                'dataverses': [
                    {'title': dataverse.title, 'alias': dataverse.alias}
                    for dataverse in dataverses
                ],
                'savedDataverse': {
                    'title': self.node_settings.dataverse,
                    'alias': self.node_settings.dataverse_alias,
                },
                'savedDataset': {
                    'title': self.node_settings.dataset,
                    'doi': self.node_settings.dataset_doi,
                }
            })

        return result

    def serialize_settings(self, node_settings, user):
        if not self.node_settings:
            self.node_settings = node_settings
        if not self.user_settings:
            self.user_settings = user.get_addon(self.addon_short_name)
        return self.serialized_node_settings
