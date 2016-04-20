from website.addons.base.serializer import OAuthAddonSerializer
from website.util import api_url_for, web_url_for

class DmptoolSerializer(OAuthAddonSerializer):

    addon_short_name = 'dmptool'

    def serialize_settings(self, node_settings, current_user, client=None):
        """View helper that returns a dictionary representation of a
        DmptoolNodeSettings record. Provides the return value for the
        Dmptool config endpoints.
        """
        valid_credentials = True
        user_settings = node_settings.user_settings
        self.node_settings = node_settings
        current_user_settings = current_user.get_addon('dmptool')
        user_is_owner = user_settings is not None and user_settings.owner == current_user


        result = {
            'userIsOwner': user_is_owner,
            'nodeHasAuth': node_settings.has_auth,
            'urls': self.addon_serialized_urls,
            'validCredentials': valid_credentials,
            'userHasAuth': current_user_settings is not None and current_user_settings.has_auth,
        }

        if node_settings.has_auth:
            # Add owner's profile URL
            result['urls']['owner'] = web_url_for(
                'profile_view_id',
                uid=user_settings.owner._id
            )
            result['ownerName'] = user_settings.owner.fullname
            # Show available folders
            # path = node_settings.folder


        return result

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner

        return {
            'auth': api_url_for('oauth_connect',
                                service_name='dmptool'),
            'importAuth': node.api_url_for('dmptool_add_user_auth'),
            'config': node.api_url_for('dmptool_set_config'),
            'deauthorize': node.api_url_for('dmptool_deauthorize_node'),
            'accounts': node.api_url_for('dmptool_get_user_settings'),
        }
