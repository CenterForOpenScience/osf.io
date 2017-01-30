from __future__ import absolute_import

import logging
from modularodm import Q

from website.app import init_app
from website.models import Node, User
from framework.mongo.utils import paginated
from scripts.analytics.base import SnapshotAnalytics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# Modified from scripts/analytics/benchmarks.py
def get_enabled_authorized_linked(user_settings_list, has_external_account, short_name):
    """ Gather the number of users who have at least one node in each of the stages for an addon

    :param user_settings_list: list of user_settings for a particualr addon
    :param has_external_account: where addon is derrived from, determines method to load node settings
    :param short_name: short name of addon to get correct node_settings
    :return:  dict with number of users that have at least one project at each stage
    """
    from addons.forward.models import NodeSettings as ForwardNodeSettings

    num_enabled = 0  # of users w/ 1+ addon account connected
    num_authorized = 0  # of users w/ 1+ addon account connected to 1+ node
    num_linked = 0  # of users w/ 1+ addon account connected to 1+ node and configured

    # osfstorage and wiki don't have user_settings, so always assume they're enabled, authorized, linked
    if short_name == 'osfstorage' or short_name == 'wiki':
        num_enabled = num_authorized = num_linked = User.find(
                    Q('is_registered', 'eq', True) &
                    Q('password', 'ne', None) &
                    Q('merged_by', 'eq', None) &
                    Q('date_disabled', 'eq', None) &
                    Q('date_confirmed', 'ne', None)
                ).count()

    elif short_name == 'forward':
        num_enabled = num_authorized = ForwardNodeSettings.find().count()
        num_linked = ForwardNodeSettings.find(Q('url', 'ne', None)).count()

    else:
        for user_settings in paginated(user_settings_list):
            if has_external_account:
                if user_settings.has_auth:
                    num_enabled += 1
                    node_settings_list = [Node.load(guid).get_addon(short_name) for guid in user_settings.oauth_grants.keys()]
            else:
                num_enabled += 1
                node_settings_list = [Node.load(guid).get_addon(short_name) for guid in user_settings.nodes_authorized]
            if any([ns.has_auth for ns in node_settings_list if ns]):
                num_authorized += 1
                if any([(ns.complete and ns.configured) for ns in node_settings_list if ns]):
                    num_linked += 1
    return {
        'enabled': num_enabled,
        'authorized': num_authorized,
        'linked': num_linked
    }


class AddonSnapshot(SnapshotAnalytics):

    @property
    def collection_name(self):
        return 'addon_snapshot'

    def get_events(self, date=None):
        super(AddonSnapshot, self).get_events(date)

        from addons.base.models import BaseNodeSettings
        from website.settings import ADDONS_AVAILABLE

        counts = []
        addons_available = {k: v for k, v in [(addon.short_name, addon) for addon in ADDONS_AVAILABLE]}

        for short_name, addon in addons_available.iteritems():

            has_external_account = hasattr(addon.settings_models.get('node'), 'external_account')

            connected_count = 0
            deleted_count = 0
            disconnected_count = 0
            node_settings_model = addon.settings_models.get('node')
            if node_settings_model:
                for node_settings in paginated(node_settings_model):
                    if node_settings.owner and not node_settings.owner.is_bookmark_collection:
                        connected_count += 1
                deleted_count = addon.settings_models['node'].find(Q('deleted', 'eq', True)).count() if addon.settings_models.get('node') else 0
                if has_external_account:
                    disconnected_count = addon.settings_models['node'].find(Q('external_account', 'eq', None) & Q('deleted', 'ne', True)).count() if addon.settings_models.get('node') else 0
                else:
                    if addon.settings_models.get('node'):
                        for nsm in addon.settings_models['node'].find(Q('deleted', 'ne', True)):
                            if nsm.configured and not nsm.complete:
                                disconnected_count += 1
            total = connected_count + deleted_count + disconnected_count
            usage_counts = get_enabled_authorized_linked(addon.settings_models.get('user'), has_external_account, addon.short_name)

            counts.append({
                'provider': {
                    'name': short_name
                },
                'users': usage_counts,
                'nodes': {
                    'total': total,
                    'connected': connected_count,
                    'deleted': deleted_count,
                    'disconnected': disconnected_count
                }
            })

            logger.info(
                '{} counted. Users with a linked node: {}, Total connected nodes: {}.'.format(
                    addon.short_name,
                    usage_counts['linked'],
                    total
                )
            )
        return counts


def get_class():
    return AddonSnapshot


if __name__ == '__main__':
    init_app()
    addon_snapshot = AddonSnapshot()
    events = addon_snapshot.get_events()
    addon_snapshot.send_events(events)
