from website.addons.base.serializer import OAuthAddonSerializer
from website.util import api_url_for

class EvernoteSerializer(OAuthAddonSerializer):

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner

        return {
            'accounts': node.api_url_for('evernote_get_user_accounts'),
        }
