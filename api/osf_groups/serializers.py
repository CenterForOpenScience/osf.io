from rest_framework import serializers as ser, exceptions
from django.core.exceptions import ValidationError

from framework.auth.core import Auth
from api.base.exceptions import InvalidModelValueError
from api.base.serializers import (
    IDField,
    LinksField,
    JSONAPISerializer,
    RelationshipField,
    TypeField,
    VersionedDateTimeField,
)
from api.base.utils import absolute_reverse
from api.nodes.serializers import CompoundIDField
from osf.models import OSFUser
from osf.models.osf_group import OSFGroup
from osf.utils.permissions import GROUP_ROLES, MEMBER, MANAGER


class GroupSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'name',
    ])

    non_anonymized_fields = [
        'type',
    ]

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    name = ser.CharField(required=True)
    date_created = VersionedDateTimeField(source='created', read_only=True)
    date_modified = VersionedDateTimeField(source='modified', read_only=True)

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    members = RelationshipField(
        related_view='groups:group-members',
        related_view_kwargs={'group_id': '<_id>'},
    )

    class Meta:
        type_ = 'groups'

    def create(self, validated_data):
        group = OSFGroup(creator=validated_data['creator'], name=validated_data['name'])
        group.save()
        return group

    def update(self, instance, validated_data):
        if 'name' in validated_data:
            instance.set_group_name(validated_data.get('name'))
            instance.save()
        return instance


class GroupDetailSerializer(GroupSerializer):
    """
    Overrides GroupSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


class GroupCompoundIDField(CompoundIDField):
    def _get_resource_id(self):
        return self.context['request'].parser_context['kwargs']['group_id']


class GroupMemberSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'role',
        'full_name',
    ])
    writeable_method_fields = frozenset([
        'role',
    ])
    non_anonymized_fields = [
        'type',
        'role',
    ]

    id = GroupCompoundIDField(source='_id', read_only=True)
    type = TypeField()
    role = ser.SerializerMethodField()
    unregistered_member = ser.SerializerMethodField()
    full_name = ser.CharField(read_only=True, source='fullname')

    users = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<_id>'},
    )

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_role(self, user):
        return user.group_role(self.context['group'])

    def get_unregistered_member(self, obj):
        unclaimed_records = obj.unclaimed_records.get(self.context['group']._id, None)
        if unclaimed_records:
            return unclaimed_records.get('name', None)

    def get_member_method(self, group, role):
        methods = {
            MANAGER: group.make_manager,
            MEMBER: group.make_member,
        }
        return methods[role]

    def get_group_role(self, validated_data, default_role):
        role = validated_data.get('role', default_role)
        if role not in GROUP_ROLES:
            raise exceptions.ValidationError('{} is not a valid role; choose manager or member.'.format(role))
        return role

    class Meta:
        type_ = 'group-members'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'groups:group-member-detail',
            kwargs={
                'user_id': obj._id,
                'group_id': self.context['request'].parser_context['kwargs']['group_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )


class GroupMemberCreateSerializer(GroupMemberSerializer):
    id = GroupCompoundIDField(source='_id', required=False, allow_null=True)
    type = TypeField()
    full_name = ser.CharField(required=False)
    email = ser.EmailField(required=False, write_only=True)

    def to_representation(self, instance, envelope='data'):
        """
        Use GroupMemberSerializer for the response, but GroupMemberCreateSerializer
        for the request.  We only want full_name to be writable on create member (for unregistered members).
        User serializer endpoints should be used to edit user's full_name.
        """
        return GroupMemberSerializer(instance=instance, context=self.context).data

    def get_user_object(self, user_id, group):
        if user_id:
            user = OSFUser.load(user_id)
            if not user:
                raise exceptions.NotFound(detail='User with id {} not found.'.format(user_id))
            if group.has_permission(user, 'member'):
                raise exceptions.ValidationError(detail='User is already a member of this group.')
            return user
        return user_id

    def create(self, validated_data):
        group = self.context['group']
        user = self.get_user_object(validated_data.get('_id', None), group)
        auth = Auth(self.context['request'].user)
        full_name = validated_data.get('full_name', None)
        email = validated_data.get('email', None)
        role = self.get_group_role(validated_data, MEMBER)

        try:
            if user:
                self.get_member_method(group, role)(user, auth)
            else:
                if not full_name or not email:
                    raise exceptions.ValidationError(detail='You must provide a full_name/email combination to add an unconfirmed member.')
                else:
                    user = group.add_unregistered_member(full_name, email, auth, role)
        except ValueError as e:
            raise exceptions.ValidationError(detail=str(e))
        except ValidationError as e:
            raise InvalidModelValueError(detail=list(e)[0])

        return user


class GroupMemberDetailSerializer(GroupMemberSerializer):
    id = GroupCompoundIDField(source='_id', required=True)

    def update(self, user, validated_data):
        group = self.context['group']
        role = self.get_group_role(validated_data, user.group_role(group))
        auth = Auth(self.context['request'].user)

        try:
            # Making sure the one-manager rule isn't violated
            self.get_member_method(self.context['group'], role)(user, auth)
        except ValueError as e:
            raise exceptions.ValidationError(detail=str(e))

        return user
