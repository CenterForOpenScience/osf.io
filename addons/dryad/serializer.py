from addons.base.serializer import CitationsAddonSerializer

class DryadSerializer(CitationsAddonSerializer):
    addon_short_name = 'dryad'

    @property
    def credentials_owner(self):
        return None

    @property
    def user_is_owner(self):
        return False

    @property
    def serialized_urls(self):
        """
            Adds in the non-standard endpoints.
        """
        urls = {}
        api_endpoints = ['dryad_validate_doi',
                'dryad_set_doi',
                'dryad_list_objects',
                'dryad_search_objects',
                'dryad_get_current_metadata',
                'dryad_citation']
        for endpoint in api_endpoints:
            urls[endpoint] = self.node_settings.owner.api_url_for(endpoint)
        return urls

    @property
    def serialized_node_settings(self):
        """
            Adds in the DOI and node_id fields to the serialized node settings.
            The DOI field is needed by the js layer for identifying the folder.
            The node_if field is needed by the js layer to copy files from
            Dryad to osfstorage.
        """
        result = super(DryadSerializer, self).serialized_node_settings
        result['doi'] = self.node_settings.dryad_package_doi
        result['node_id'] = self.node_settings.owner._id
        return result
