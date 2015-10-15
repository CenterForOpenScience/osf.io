from rest_framework import serializers as ser

from api.base.serializers import (
    IDField,
    JSONAPIHyperlinkedIdentityField,
    JSONAPIListField,
    JSONAPISerializer,
    LinksField,
)
from api.nodes.serializers import NodeSerializer, NodeTagField

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

    nodes = JSONAPIHyperlinkedIdentityField(
        view_name='user-addons:user-addon-nodes',
        lookup_field='pk',
        lookup_url_kwarg='user_addon_id',
        link_type='related'
    )

    def get_short_name(self, instance):
        return instance.config.short_name

    def get_full_name(self, instance):
        return instance.config.full_name


class UserAddonNodeSerializer(NodeSerializer):

    filterable_fields = ()

    node_id = IDField(source='_id', required=True)
    external_account_id = ser.CharField(required=True)

    category_choices = Node.CATEGORY_MAP.keys()
    category_choices_string = ', '.join(["'{}'".format(choice) for choice in category_choices])

    title = ser.CharField(read_only=True)
    description = ser.CharField(allow_blank=True, allow_null=True, read_only=True)
    category = ser.ChoiceField(choices=category_choices, help_text="Choices: " + category_choices_string, read_only=True)
    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    registration = ser.BooleanField(read_only=True, source='is_registration')
    fork = ser.BooleanField(read_only=True, source='is_fork')
    collection = ser.BooleanField(read_only=True, source='is_folder')
    dashboard = ser.BooleanField(read_only=True, source='is_dashboard')
    tags = JSONAPIListField(child=NodeTagField(), read_only=True)

    # Public is only write-able by admins--see update method
    public = ser.BooleanField(source='is_public',
                              help_text='Nodes that are made public will give read-only access '
                                        'to everyone. Private nodes require explicit read '
                                        'permission. Write and admin access are the same for '
                                        'public and private nodes. Administrators on a parent '
                                        'node have implicit read permissions for all child nodes',
                              read_only=True)

    links = LinksField({})

    class Meta:
        type_ = 'linked_nodes'

    def perform_create(self, instance):
        current_user_auth = Auth(self.request.user)
        user_addon = self.get_user_addon()
        node_id = serializer.validated_data['_id']
        node = get_object_or_error(
            Node,
            node_id,
            'node'
        )
        external_account = self.get_external_account(kwargs=serializer.validated_data)
        if node.can_edit(auth=current_user_auth):
            node_addon = node.get_or_add_addon(user_addon.config.short_name, auth=current_user_auth)
            node_addon.authorize(external_account, auth=current_user_auth)
            serializer.save()
        else:
            raise PermissionDenied()

