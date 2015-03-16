from website.serializers import OsfSerializer
from website.serializers.oauth import ExternalAccountSerializer


class UserSerializer(OsfSerializer):
    excluded_for_export = [
        'api_keys',  # security
        'comments_viewed_timestamp',  # state/presentation
        'date_disabled',  # not applicable
        'date_last_login',  # state/presentation
        'email_verifications',  # security
        'locale',  # state/presentation
        'mailing_lists',  # state/presentation
        'password',  # security
        'piwik_token',  # security
        'recently_added',  # state/presentation
        'system_tags',  # state/presentation
        'timezone',  # state/presentation
        'verification_key',  # security
        'watched',  # state/presentation
    ]

    def export(self):
        retval = {
            k: v
            for k, v in self.model.to_storage().iteritems()
            if not (k in self._excluded_modm or k in self.excluded_for_export)
        }

        retval['external_accounts'] = [
            ExternalAccountSerializer(external_account).export()
            for external_account in self.model.external_accounts
        ]

        return retval