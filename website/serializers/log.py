from website.serializers import OsfSerializer


class LogSerializer(OsfSerializer):
    excluded_for_export = [
        'api_key'
    ]

    def export(self):
        retval = {
            k: v
            for k, v in self.model.to_storage().iteritems()
            if not (k in self._excluded_modm or k in self.excluded_for_export)
        }

        return retval