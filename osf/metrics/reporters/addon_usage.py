from datetime import timedelta
import logging

from django.utils import timezone

from osf.metrics.reports import AddonUsageReport
from osf.models import OSFUser, AbstractNode
from framework.database import paginated
from website import settings
from ._base import DailyReporter

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
        num_enabled = num_authorized = num_linked = OSFUser.objects.filter(
            is_registered=True,
            password__isnull=False,
            merged_by__isnull=True,
            date_disabled__isnull=True,
            date_confirmed__isnull=False
        ).count()

    elif short_name == 'forward':
        num_enabled = num_authorized = ForwardNodeSettings.objects.count()
        num_linked = ForwardNodeSettings.objects.filter(url__isnull=False).count()

    else:
        for user_settings in paginated(user_settings_list):
            node_settings_list = []
            if has_external_account:
                if user_settings.has_auth:
                    num_enabled += 1
                    node_settings_list = [AbstractNode.load(guid).get_addon(short_name) for guid in user_settings.oauth_grants.keys()]
            else:
                num_enabled += 1
                node_settings_list = [AbstractNode.load(guid).get_addon(short_name) for guid in user_settings.nodes_authorized]
            if any([ns.has_auth for ns in node_settings_list if ns]):
                num_authorized += 1
                if any([(ns.complete and ns.configured) for ns in node_settings_list if ns]):
                    num_linked += 1
    return {
        'enabled': num_enabled,
        'authorized': num_authorized,
        'linked': num_linked
    }


class AddonUsageReporter(DailyReporter):
    def report(self, date):
        yesterday = timezone.now().date() - timedelta(days=1)
        if date != yesterday:
            raise NotImplementedError

        reports = []
        addons_available = {
            addon.short_name: addon
            for addon in settings.ADDONS_AVAILABLE
        }

        for short_name, addon in addons_available.items():

            has_external_account = hasattr(addon.models.get('nodesettings'), 'external_account')

            connected_count = 0
            deleted_count = 0
            disconnected_count = 0
            node_settings_model = addon.models.get('nodesettings')
            if node_settings_model:
                for node_settings in paginated(node_settings_model):
                    if node_settings.owner and not node_settings.owner.all_tags.filter(name='old_node_collection', system=True).exists():
                        connected_count += 1
                deleted_count = addon.models['nodesettings'].objects.filter(deleted__isnull=False).count() if addon.models.get('nodesettings') else 0
                if has_external_account:
                    disconnected_count = addon.models['nodesettings'].objects.filter(external_account__isnull=True, is_deleted=False).count() if addon.models.get('nodesettings') else 0
                else:
                    if addon.models.get('nodesettings'):
                        for nsm in addon.models['nodesettings'].objects.filter(deleted__isnull=True):
                            if nsm.configured and not nsm.complete:
                                disconnected_count += 1
            total = connected_count + deleted_count + disconnected_count
            usage_counts = get_enabled_authorized_linked(addon.models.get('usersettings'), has_external_account, addon.short_name)

            reports.append(
                AddonUsageReport(
                    report_date=date,
                    addon_shortname=short_name,
                    users_enabled_count=usage_counts['enabled'],
                    users_authorized_count=usage_counts['authorized'],
                    users_linked_count=usage_counts['linked'],
                    nodes_total_count=total,
                    nodes_connected_count=connected_count,
                    nodes_deleted_count=deleted_count,
                    nodes_disconnected_count=disconnected_count,
                )
            )

            logger.info(
                '{} counted. Users with a linked node: {}, Total connected nodes: {}.'.format(
                    addon.short_name,
                    usage_counts['linked'],
                    total
                )
            )
        return reports

    def keen_events_from_report(self, report):
        event = {
            'provider': {
                'name': report.addon_shortname,
            },
            'users': {
                'enabled': report.users_enabled_count,
                'authorized': report.users_authorized_count,
                'linked': report.users_linked_count,
            },
            'nodes': {
                'total': report.nodes_total_count,
                'connected': report.nodes_connected_count,
                'deleted': report.nodes_deleted_count,
                'disconnected': report.nodes_disconnected_count
            },
        }
        return {'addon_snapshot': [event]}
