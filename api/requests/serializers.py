from django.db import IntegrityError
from rest_framework import exceptions
from rest_framework import serializers as ser

from api.base.exceptions import Conflict
from api.base.utils import absolute_reverse, get_user_auth
from api.base.serializers import JSONAPISerializer, LinksField, VersionedDateTimeField, RelationshipField
from osf.models import NodeRequest, PreprintRequest
from osf.utils.workflows import DefaultStates, RequestTypes
from osf.utils import permissions as osf_permissions


class RequestSerializer(JSONAPISerializer):
    class Meta:
        type_ = 'node-requests'

    filterable_fields = frozenset([
        'creator',
        'request_type',
        'current_state',
        'created',
        'id'
    ])
    id = ser.CharField(source='_id', read_only=True)
    request_type = ser.ChoiceField(read_only=True, required=False, choices=RequestTypes.choices())
    machine_state = ser.ChoiceField(read_only=True, required=False, choices=DefaultStates.choices())
    comment = ser.CharField(required=False, allow_blank=True, max_length=65535)
    created = VersionedDateTimeField(read_only=True)
    modified = VersionedDateTimeField(read_only=True)
    date_last_transitioned = VersionedDateTimeField(read_only=True)

    creator = RelationshipField(
        read_only=True,
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<creator._id>'},
        filter_key='creator___id',
    )

    links = LinksField({
        'self': 'get_absolute_url',
        'target': 'get_target_url'
    })

    @property
    def target(self):
        raise NotImplementedError()

    def get_absolute_url(self, obj):
        return absolute_reverse('requests:request-detail', kwargs={'request_id': obj._id, 'version': self.context['request'].parser_context['kwargs']['version']})

    def get_target_url(self, obj):
        raise NotImplementedError()

    def create(self, validated_data):
        raise NotImplementedError()

class NodeRequestSerializer(RequestSerializer):
    class Meta:
        type_ = 'node-requests'

    target = RelationshipField(
        read_only=True,
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<target._id>'},
        filter_key='target___id',
    )

    def get_target_url(self, obj):
        return absolute_reverse('nodes:node-detail', kwargs={'node_id': obj.target._id, 'version': self.context['request'].parser_context['kwargs']['version']})

class NodeRequestCreateSerializer(NodeRequestSerializer):
    request_type = ser.ChoiceField(required=True, choices=RequestTypes.choices())

    def create(self, validated_data):
        auth = get_user_auth(self.context['request'])
        if not auth.user:
            raise exceptions.PermissionDenied

        try:
            node = self.context['view'].get_target()
        except exceptions.PermissionDenied:
            node = self.context['view'].get_target(check_object_permissions=False)
            if auth.user in node.contributors:
                raise exceptions.PermissionDenied('You cannot request access to a node you contribute to.')
            raise

        comment = validated_data.pop('comment', '')
        request_type = validated_data.pop('request_type', None)

        if request_type != RequestTypes.ACCESS.value:
            raise exceptions.ValidationError('You must specify a valid request_type.')

        try:
            node_request = NodeRequest.objects.create(
                target=node,
                creator=auth.user,
                comment=comment,
                machine_state=DefaultStates.INITIAL.value,
                request_type=request_type
            )
            node_request.save()
        except IntegrityError:
            raise Conflict('Users may not have more than one {} request per node.'.format(request_type))
        node_request.run_submit(auth.user)
        return node_request

class PreprintRequestSerializer(RequestSerializer):
    class Meta:
        type_ = 'preprint-requests'

    target = RelationshipField(
        read_only=True,
        related_view='preprints:preprint-detail',
        related_view_kwargs={'preprint_id': '<target._id>'},
        filter_key='target___id',
    )

    def get_target_url(self, obj):
        return absolute_reverse('preprints:preprint-detail', kwargs={'preprint_id': obj.target._id, 'version': self.context['request'].parser_context['kwargs']['version']})

class PreprintRequestCreateSerializer(PreprintRequestSerializer):
    request_type = ser.ChoiceField(required=True, choices=RequestTypes.choices())

    def create(self, validated_data):
        auth = get_user_auth(self.context['request'])
        if not auth.user:
            raise exceptions.PermissionDenied

        preprint = self.context['view'].get_target()

        if not preprint.has_permission(auth.user, osf_permissions.ADMIN):
            raise exceptions.PermissionDenied

        comment = validated_data.pop('comment', '')
        request_type = validated_data.pop('request_type', None)

        if PreprintRequest.objects.filter(target_id=preprint.id, creator_id=auth.user.id, request_type=request_type).exists():
            raise Conflict('Users may not have more than one {} request per preprint.'.format(request_type))

        if request_type != RequestTypes.WITHDRAWAL.value:
            raise exceptions.ValidationError('You must specify a valid request_type.')

        preprint_request = PreprintRequest.objects.create(
            target=preprint,
            creator=auth.user,
            comment=comment,
            machine_state=DefaultStates.INITIAL.value,
            request_type=request_type
        )
        preprint_request.save()
        preprint_request.run_submit(auth.user)
        return preprint_request
