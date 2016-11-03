import logging
from modularodm import Q

from website.app import init_app
from scripts.analytics.base import SnapshotAnalytics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class AddonSnapshot(SnapshotAnalytics):

    @property
    def collection_name(self):
        return 'addon_snapshot'

    def get_events(self, date=None):
        super(AddonSnapshot, self).get_events(date)

        from website.settings import ADDONS_AVAILABLE
        counts = []
        addons_available = {k: v for k, v in [(addon.short_name, addon) for addon in ADDONS_AVAILABLE]}

        for short_name, addon in addons_available.iteritems():
            user_count = addon.settings_models['user'].find().count() if addon.settings_models.get('user') else 0
            connected_count = addon.settings_models['node'].find().count() if addon.settings_models.get('node') else 0
            deleted_count = addon.settings_models['node'].find(Q('deleted', 'eq', True)).count() if addon.settings_models.get('node') else 0
            disconnected_count = addon.settings_models['node'].find(Q('external_account', 'eq', None) & Q('deleted', 'ne', True)).count() if addon.settings_models.get('node') else 0
            total = connected_count + deleted_count + disconnected_count
            counts.append({
                'provider': {
                    'name': short_name
                },
                'users': {
                    'total': user_count
                },
                'nodes': {
                    'total': total,
                    'connected': connected_count,
                    'deleted': deleted_count,
                    'disconnected': disconnected_count
                }
            })

            logger.info('{} counted. Users: {}, Total Nodes: {}'.format(addon.short_name, user_count, total))

        return counts


def get_class():
    return AddonSnapshot


if __name__ == '__main__':
    init_app()
    addon_snapshot = AddonSnapshot()
    events = addon_snapshot.get_events()
    addon_snapshot.send_events(events)
