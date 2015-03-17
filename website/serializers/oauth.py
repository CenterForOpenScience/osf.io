from website.serializers import OsfSerializer


class ExternalAccountSerializer(OsfSerializer):
    excluded_for_export = [
        'oauth_secret',  # security
        'oauth_key',  # security
        'refresh_token',  # security
        'expires_at',  # security
    ]

    def export(self):
        retval = {
            k: v
            for k, v in self.model.to_storage().iteritems()
            if not (k in self._excluded_modm or k in self.excluded_for_export)
        }

        return retval