# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import serializers as ser

from api.base.utils import absolute_reverse
from api.base.serializers import JSONAPISerializer
from api.base.serializers import RelationshipField
from api.base.serializers import LinksField

from reviews.models import ReviewLog
from reviews.models import ReviewProviderMixin
from reviews.models import ReviewableMixin


class ReviewLogSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'from_state',
        'to_state',
        'date_created',
        'date_modified',
        'creator',
        'provider',
        'reviewable',
    ])

    id = ser.CharField(source='_id', required=True)

    from_state = ser.CharField(max_length=15)
    to_state = ser.CharField(max_length=15)

    # TODO what limit do we want?
    comment = ser.CharField(max_length=65535)

    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)

    provider = RelationshipField(
        related_view='preprint_providers:preprint_provider-detail',
        related_view_kwargs={'provider_id': '<reviewable.provider._id>'},
    )

    reviewable = RelationshipField(
        related_view='preprints:preprint-detail',
        related_view_kwargs={'preprint_id': '<reviewable._id>'},
    )

    creator = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
    )

    links = LinksField(
        {
            'self': 'get_log_url',
        }
    )

    def get_log_url(self, obj):
        return absolute_reverse('reviews:review_log-detail', kwargs={'log_id': obj._id, 'version': self.context['request'].parser_context['kwargs']['version']})

    class Meta:
        type_ = 'review_logs'
