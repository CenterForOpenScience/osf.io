from website.serializers import OsfSerializer
from website.serializers.log import LogSerializer


class NodeSerializer(OsfSerializer):
    excluded_for_export = [
        'is_dashboard',
        'wiki_private_uuids',  # ?
        'is_folder',
        'users_watching_node',
        'child_node_subscriptions',
        'piwik_site_id',
        'wiki_pages_versions',  # ?
        'wiki_pages_current',  # ?
        'system_tags',
        'api_keys',
        'permissions',
        'deleted_date',
        'is_deleted',
        'expanded',
        'nodes',
    ]

    def export(self):
        retval = {
            k: v
            for k, v in self.model.to_storage().iteritems()
            if not (k in self._excluded_modm or k in self.excluded_for_export)
        }

        parent = self.model.parent_node
        retval['parent_node'] = parent._id if parent else None

        retval['logs'] = [
            LogSerializer(log).export()
            for log in self.model.logs
        ]

        return retval