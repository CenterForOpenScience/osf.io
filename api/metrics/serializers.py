import datetime

from rest_framework import serializers as ser

from api.base.serializers import BaseAPISerializer
from api.base.utils import absolute_reverse
from osf.metrics.counted_usage import CountedUsageV3
from website import settings as website_settings


class PreprintMetricSerializer(BaseAPISerializer):

    query = ser.DictField()

    class Meta:
        type_ = 'preprint_metrics'


class RawMetricsSerializer():

    query = ser.DictField()


def validate_action_label(label):
    try:
        CountedUsageV3.ActionLabel(label)
    except ValueError:
        valid_labels = ', '.join(label.value for label in CountedUsageV3.ActionLabel)
        raise ser.ValidationError(
            f'Invalid value in action_labels! Valid labels: {valid_labels}',
        )


class PageviewInfoSerializer(ser.Serializer):
    page_url = ser.URLField(max_length=4095, required=True)
    page_title = ser.CharField(max_length=4095, required=False)
    referer_url = ser.URLField(max_length=4095, required=False, allow_blank=True)
    route_name = ser.CharField(max_length=4095, required=False)


class CountedUsageSerializer(ser.Serializer):
    item_guid = ser.CharField(max_length=255, required=False)
    item_public = ser.BooleanField(required=False)
    client_session_id = ser.CharField(max_length=255, required=False)

    action_labels = ser.ListField(
        child=ser.CharField(validators=[validate_action_label]),
        allow_empty=False,
        max_length=255,
    )

    # when the "usage" is viewing a web page, include pageview info
    pageview_info = PageviewInfoSerializer(required=False)

    def validate(self, data):
        no_guid = not data.get('item_guid')
        no_page_url = not data.get('pageview_info', {}).get('page_url')
        if no_guid and no_page_url:
            raise ser.ValidationError(f'Either item_guid or pageview_info.page_url is required({data})')
        return data

    def create(self, validated_data):
        return CountedUsageV3.record(
            platform_iri=website_settings.DOMAIN,
            item_guid=validated_data.get('item_guid'),
            item_public=validated_data.get('item_public'),
            session_id=validated_data['session_id'],  # must be provided by the view
            action_labels=validated_data.get('action_labels'),
            pageview_info=validated_data.get('pageview_info'),
        )


class ReportNameSerializer(ser.BaseSerializer):
    def to_representation(self, instance):
        recent_link = absolute_reverse(
            'metrics:recent-report-list',
            kwargs={'report_name': instance},
        )
        return {
            'id': instance,
            'type': 'metrics-report-name',
            'links': {
                'recent': recent_link,
            },
        }


class DailyReportSerializer(ser.BaseSerializer):
    def to_representation(self, instance):
        # TODO: detangle datamodel (osf.metrics.reports) from api serialization
        # (don't use `to_dict` here)
        report_as_dict = instance.to_dict()
        report_name = self.context['report_name']
        report_date = report_as_dict['report_date']

        if isinstance(report_date, datetime.datetime):
            report_date = report_date.date()
        if isinstance(report_date, datetime.date):
            report_date = str(report_date)

        return {
            'id': instance.meta.id,
            'type': f'daily-report:{report_name}',
            'attributes': {
                **report_as_dict,
                'report_date': report_date,
            },
        }


class NodeAnalyticsSerializer(ser.BaseSerializer):
    def to_representation(self, instance):
        aggs = instance.aggregations
        popular_pages = [
            {
                'path': bucket['key'],
                'route': bucket['route-for-path'].buckets[0]['key'],
                'title': bucket['title-for-path'].buckets[0]['key'],
                'count': bucket['doc_count'],
            }
            for bucket in aggs['popular-pages'].buckets
        ]
        unique_visits = [
            {
                'date': bucket['key_as_string'],
                'count': bucket['doc_count'],
            }
            for bucket in aggs['unique-visits'].buckets
        ]
        time_of_day = [
            {
                'hour': bucket['key'],
                'count': bucket['doc_count'],
            }
            for bucket in aggs['time-of-day'].buckets
        ]
        referer_domain = [
            {
                'referer_domain': bucket['key'],
                'count': bucket['doc_count'],
            }
            for bucket in aggs['referer-domain'].buckets
        ]
        node_guid = self.context['node_guid']
        timespan = self.context['timespan']
        return {
            'id': f'{node_guid}:{timespan}',
            'type': 'node-analytics',
            'attributes': {
                'popular_pages': popular_pages,
                'unique_visits': unique_visits,
                'time_of_day': time_of_day,
                'referer_domain': referer_domain,
            },
        }
