import logging

from django.db import connection
from django.db.models import (
    Count,
    Func,
    BigIntegerField,
    Q,
    Sum,
)

from addons.base.models import BaseOAuthUserSettings, BaseOAuthNodeSettings
from osf.metrics.reports import StorageAddonUsage, RunningTotal, UsageByStorageAddon
from osf.models import SpamStatus, Tag
from website import settings
from ._base import DailyReporter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def storage_addon_node_counts(date, nodesettings_model):
    nodesettings_qs = (
        nodesettings_model.objects
        .exclude(owner__isnull=True)
        .exclude(owner__deleted__isnull=False)
        .exclude(owner__spam_status=SpamStatus.SPAM)
    )
    try:
        old_node_collection_tag = Tag.all_tags.get(system=True, name='old_node_collection')
    except Tag.DoesNotExist:
        pass
    else:
        nodesettings_qs = nodesettings_qs.exclude(owner__tags=old_node_collection_tag)

    created_before = Q(created__date__lte=date)
    created_today = Q(created__date=date)
    deleted_before = Q(deleted__date__lte=date)
    deleted_today = Q(deleted__date=date)

    addon_is_oauth = issubclass(nodesettings_model, BaseOAuthNodeSettings)
    if addon_is_oauth:
        is_connected = (~deleted_before & Q(external_account__isnull=False))
    else:
        is_connected = (~deleted_before)

    aggregates = {
        'connected_total': Count('pk', filter=(is_connected & created_before)),
        'connected_daily': Count('pk', filter=(is_connected & created_today)),
        'deleted_total': Count('pk', filter=(deleted_before)),
        'deleted_daily': Count('pk', filter=(deleted_today)),
    }
    if addon_is_oauth:
        is_disconnected = (~deleted_before & Q(external_account__isnull=True))
        aggregates.update({
            'disconnected_total': Count('pk', filter=(is_disconnected & created_before)),
            'disconnected_daily': Count('pk', filter=(is_disconnected & created_today)),
        })
    return nodesettings_qs.aggregate(**aggregates)


def storage_addon_user_counts(date, usersettings_model):
    usersettings_qs = (
        usersettings_model.objects
        .exclude(owner__deleted__isnull=False)
        .exclude(owner__spam_status=SpamStatus.SPAM)
    )

    created_before = Q(created__date__lte=date)
    created_today = Q(created__date=date)
    deleted_before = Q(deleted__date__lte=date)
    deleted_today = Q(deleted__date=date)

    aggregates = {
        'enabled_total': Count('pk', filter=(~deleted_before & created_before)),
        'enabled_daily': Count('pk', filter=(~deleted_before & created_today)),
        'deleted_total': Count('pk', filter=(deleted_before)),
        'deleted_daily': Count('pk', filter=(deleted_today)),
    }
    if issubclass(usersettings_model, BaseOAuthUserSettings):
        # adding a temporary function (in the pg_temp schema) to contain
        # all jsonb shenanigans -- this function counts the number of
        # '<ExternalAccount._id>' keys nested one level deep
        # (see addons.base.models.BaseOAuthUserSettings for the expected
        # structure of `oauth_grants`)
        temp_function__count_oauth_grants = '''
            CREATE OR REPLACE FUNCTION
            pg_temp.count_oauth_grants(usersettings_oauth_grants jsonb)
            RETURNS bigint AS $$
                SELECT count(*)
                FROM jsonb_object_keys(usersettings_oauth_grants) AS guid
                INNER JOIN LATERAL jsonb_object_keys(jsonb_extract_path(usersettings_oauth_grants, guid)) AS account_id ON TRUE
            $$ LANGUAGE SQL;
        '''
        with connection.cursor() as cursor:
            cursor.execute(temp_function__count_oauth_grants)

        usersettings_qs = usersettings_qs.annotate(
            grant_count=Func('oauth_grants', function='pg_temp.count_oauth_grants'),
        )
        # each "grant" is a "link" to a node
        has_link = ~deleted_before & Q(grant_count__gt=0)
        aggregates.update({
            'linked_total': Count('pk', filter=(has_link & created_before)),
            'linked_daily': Count('pk', filter=(has_link & created_today)),
            'link_count_total': Sum(
                'grant_count',
                filter=(~deleted_before & created_before),
                output_field=BigIntegerField(),
            ),
            'link_count_daily': Sum(
                'grant_count',
                filter=(~deleted_before & created_today),
                output_field=BigIntegerField(),
            ),
        })
    return usersettings_qs.aggregate(**aggregates)


class StorageAddonUsageReporter(DailyReporter):
    def report(self, date):
        storage_addon_configs = {
            addon_config.short_name: addon_config
            for addon_config in settings.ADDONS_AVAILABLE
            if 'storage' in addon_config.categories
        }

        usage_by_addon = []
        for short_name, addon_config in storage_addon_configs.items():
            user_counts = storage_addon_user_counts(date, addon_config.get_model('UserSettings'))
            node_counts = storage_addon_node_counts(date, addon_config.get_model('NodeSettings'))

            usage_by_addon.append(
                UsageByStorageAddon(
                    addon_shortname=short_name,
                    enabled_usersettings=RunningTotal(
                        total=user_counts.get('enabled_total', 0),
                        total_daily=user_counts.get('enabled_daily', 0),
                    ),
                    deleted_usersettings=RunningTotal(
                        total=user_counts.get('deleted_total', 0),
                        total_daily=user_counts.get('deleted_daily', 0),
                    ),
                    linked_usersettings=RunningTotal(
                        total=user_counts.get('linked_total', 0),
                        total_daily=user_counts.get('linked_daily', 0),
                    ),
                    usersetting_links=RunningTotal(
                        total=user_counts.get('link_count_total', 0),
                        total_daily=user_counts.get('link_count_daily', 0),
                    ),
                    connected_nodesettings=RunningTotal(
                        total=node_counts.get('connected_total', 0),
                        total_daily=node_counts.get('connected_daily', 0),
                    ),
                    disconnected_nodesettings=RunningTotal(
                        total=node_counts.get('disconnected_total', 0),
                        total_daily=node_counts.get('disconnected_daily', 0),
                    ),
                    deleted_nodesettings=RunningTotal(
                        total=node_counts.get('deleted_total', 0),
                        total_daily=node_counts.get('deleted_daily', 0),
                    ),
                )
            )
        return [StorageAddonUsage(
            report_date=date,
            usage_by_addon=usage_by_addon,
        )]

    def keen_events_from_report(self, report):
        events = [
            {
                'provider': {
                    'name': addon_usage.addon_shortname,
                },
                'users': {
                    'enabled': addon_usage.enabled_usersettings,
                    'linked': addon_usage.linked_usersettings,
                },
                'nodes': {
                    'connected': addon_usage.connected_nodesettings,
                    'deleted': addon_usage.deleted_nodesettings,
                    'disconnected': addon_usage.disconnected_nodesettings
                },
            }
            for addon_usage in report.usage_by_addon
        ]
        return {'addon_snapshot': events}
