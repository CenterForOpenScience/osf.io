from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers as ser

from framework.auth import Auth

from website.models import Node

from api.base.utils import get_object_or_error
from api.base.serializers import (
    JSONAPISerializer, JSONAPIHyperlinkedIdentityField, IDField
)


class ExternalAccountField(JSONAPIHyperlinkedIdentityField):

    def __init__(self, **kwargs):
        kwargs['queryset'] = True
        kwargs['read_only'] = False
        kwargs['allow_null'] = True
        kwargs['lookup_field'] = 'pk'
        kwargs['lookup_url_kwarg'] = 'external_account_id'

        self.meta = None
        self.link_type = 'related'

        super(ser.HyperlinkedIdentityField, self).__init__(view_name='external-accounts:external-account-detail', **kwargs)

    def get_queryset(self):
        pass

    def get_url(self, obj, view_name, request, format):
        if obj is None:
            return None
        return super(ser.HyperlinkedIdentityField, self).get_url(obj, view_name, request, format)

    def to_internal_value(self, data):
        if data is None:
            return None
        pass

class NodeAddonSerializer(JSONAPISerializer):

    class Meta:
        type_ = 'node_addons'

    id = IDField(source='_id', read_only=True)
    short_name = ser.SerializerMethodField(read_only=True)
    full_name = ser.SerializerMethodField(read_only=True)

    # TODO addon config

    node = JSONAPIHyperlinkedIdentityField(
        view_name='nodes:node-detail',
        lookup_field='pk',
        lookup_url_kwarg='node_id',
        link_type='related'
    )

    external_account = ExternalAccountField(
        lookup_field='pk',
        lookup_url_kwarg='external_account_id',
    )

    def get_short_name(self, instance):
        return instance.config.short_name

    def get_full_name(self, instance):
        return instance.config.full_name

    def create(self, validated_data):
        current_user_auth = Auth(self.context['request'].user)
        view = self.context['view']
        user_addon = view.get_user_addon()
        node_id = validated_data['_id']
        node = get_object_or_error(
            Node,
            node_id,
            'node'
        )
        external_account = view.get_external_account(kwargs=validated_data)
        if node.can_edit(auth=current_user_auth):
            node_addon = node.get_or_add_addon(user_addon.config.short_name, auth=current_user_auth)
            node_addon.authorize(external_account, auth=current_user_auth)
            return node_addon
        else:
            raise PermissionDenied()
