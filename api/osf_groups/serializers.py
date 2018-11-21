from rest_framework import serializers as ser, exceptions

from django.db.models import OuterRef, Subquery
from api.base.serializers import (
    IDField,
    LinksField,
    JSONAPISerializer,
    RelationshipField,
    TypeField,
    VersionedDateTimeField,
)
from osf.models import OSFGroup, OSFUser, Guid


class OSFGroupSerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'name',
    ])

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

    managers = RelationshipField(
        related_view='osf_groups:group-managers',
        related_view_kwargs={'group_id': '<_id>'},
        read_only=False,
        many=True,
        required=False,
    )

    members = RelationshipField(
        related_view='osf_groups:group-members',
        related_view_kwargs={'group_id': '<_id>'},
        read_only=False,
        many=True,
        required=False,
    )

    class Meta:
        type_ = 'osf_groups'

    def user_qs(self, user_list):
        guids = Guid.objects.filter(content_type__model='osfuser', object_id=OuterRef('pk'))
        user_qs = OSFUser.objects.annotate(
            guid=Subquery(guids.values('_id')[:1]),
        ).filter(
            guid__in=user_list, is_registered=True, date_disabled__isnull=True,
        )
        if user_qs.count() < len(user_list):
            raise exceptions.NotFound(detail='User was not found')
        return user_qs

    # Custom validation of manager field
    def validate_managers(self, data):
        # Managers don't have to be specified.  However, if they are specified, it will be an entire
        # overwrite and the creator's id must be included in this list
        managers = data or []
        request = self.context['request']
        if request.method == 'POST' and request.user._id not in managers:
            raise exceptions.ValidationError('You must specify yourself as a manager when creating an OSF Group.')
        return data

    def update_group_membership(self, validated_data, group):
        """
        Updates the osf group's member and/or manager list to match guids provided.
        Member/Manager relationships don't have to be provided, but if they are, it will be a total overwrite.

        Sending in an empty list completely removes all the members (cannot do this for managers).
        There must be at least one manager of the osf group.
        """
        managers = self.user_qs(validated_data.get('managers', []))
        members = self.user_qs(validated_data.get('members', []))
        if (managers & members).exists():
            raise exceptions.ValidationError('You cannot specify a user as both a member and a manager of an OSF Group.')

        if 'managers' in validated_data:
            to_remove = group.managers.exclude(id__in=managers)
            to_add = managers.exclude(id__in=group.managers)
            for user in to_add:
                group.make_manager(user)
            for user in to_remove:
                try:
                    # Removing a manager has the potential to violate the one-manager rule
                    group.remove_manager(user)
                except ValueError as e:
                    raise exceptions.ValidationError(detail=e)

        if 'members' in validated_data:
            to_remove = group.members_only.exclude(id__in=members)
            to_add = members.exclude(id__in=group.members_only)
            for user in to_remove:
                group.remove_member(user)
            for user in to_add:
                try:
                    # Making someone a member has the potential to violate the one-manager rule
                    # (This either adds a new user as a member or downgrades a manager to a member)
                    group.make_member(user)
                except ValueError as e:
                    raise exceptions.ValidationError(detail=e)
        return

    def create(self, validated_data):
        group = OSFGroup(creator=validated_data['creator'], name=validated_data['name'])
        group.save()
        self.update_group_membership(validated_data, group)
        return group

    def update(self, instance, validated_data):
        if 'name' in validated_data:
            instance.set_group_name(validated_data.get('name'))
        self.update_group_membership(validated_data, instance)
        instance.save()
        return instance


class OSFGroupDetailSerializer(OSFGroupSerializer):
    """
    Overrides OSFGroupSerializer to make id required.
    """
    id = IDField(source='_id', required=True)
