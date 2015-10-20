from rest_framework import serializers as ser

from api.base.serializers import (
    IDField,
    JSONAPIHyperlinkedIdentityField,
    JSONAPISerializer,
    TypeField,
    TargetTypeField,
    TargetIDField,
)
from api.base.utils import get_object_or_error

from framework.auth import Auth

from website.models import Node

class UserAddonSerializer(JSONAPISerializer):

    class Meta:
        type_ = 'user_addons'

    id = IDField(source='_id')
    short_name = ser.SerializerMethodField()
    full_name = ser.SerializerMethodField()

    external_accounts = JSONAPIHyperlinkedIdentityField(
        view_name='user-addons:user-addon-external-accounts',
        lookup_field='pk',
        lookup_url_kwarg='user_addon_id',
        link_type='related'
    )

    node_addons = JSONAPIHyperlinkedIdentityField(
        view_name='user-addons:user-addon-node-addons',
        lookup_field='pk',
        lookup_url_kwarg='user_addon_id',
        link_type='related'
    )

    def get_short_name(self, instance):
        return instance.config.short_name

    def get_full_name(self, instance):
        return instance.config.full_name

class UserAddonLinkedNodeSerializer(JSONAPISerializer):

    id = IDField(source='_id', required=True)
    type = TypeField()

    node = JSONAPIHyperlinkedIdentityField(
        view_name='nodes:node-detail',
        lookup_field='owner_id',
        lookup_url_kwarg='node_id',
        link_type='related'
    )
    node_addon = JSONAPIHyperlinkedIdentityField(
        view_name='node-addons:node-addon-detail',
        lookup_field='pk',
        lookup_url_kwarg='node_addon_id',
        link_type='related'
    )

    class Meta:
        type_ = 'linked_nodes'
        target_type_ = 'external_accounts'

    def is_valid(self, **kwargs):
        external_account_id = self.initial_data.get('id')
        super(UserAddonLinkedNodeSerializer, self).is_valid()
        self.validated_data['external_account_id'] = external_account_id

    def create(self, validated_data):
        view = self.context['view']

        node = get_object_or_error(
            Node,
            validated_data.get('_id'),
            'node'
        )
        user_addon = view.get_user_addon()
        external_account = view.get_external_account(kwargs={
            'external_account_id': validated_data['target_id']
        })

        provider = user_addon.config.short_name
        node_addon = node.get_or_add_addon(provider)
        node_addon.authorize(
            external_account,
            auth=Auth(self.context['request'].user)
        )
        return node_addon


class UserAddonLinkedNodeCreateSerializer(UserAddonLinkedNodeSerializer):

    target_type = TargetTypeField()
    target_id = TargetIDField(write_only=True)
