from api.base.serializers import BaseAPISerializer
from rest_framework import serializers as ser


class PreprintMetricSerializer(BaseAPISerializer):

    query = ser.DictField()

    class Meta:
        type_ = 'preprint_metrics'


class RawMetricsSerializer():

    query = ser.DictField()
