from django.db import IntegrityError
from rest_framework import exceptions
from rest_framework import serializers as ser

from api.base.exceptions import Conflict
from api.base.utils import absolute_reverse, get_user_auth
from api.base.serializers import (
    JSONAPISerializer,
    LinksField,
    VersionedDateTimeField,
    RelationshipField,
)
from osf.models import (
    NodeRequest,
    PreprintRequest,
    Institution,
    OSFUser,
)
from osf.utils.workflows import DefaultStates, RequestTypes, NodeRequestTypes
from osf.utils import permissions as osf_permissions
from website import settings
from website.mails import send_mail, NODE_REQUEST_INSTITUTIONAL_ACCESS_REQUEST


class RequestSerializer(JSONAPISerializer):
    class Meta:
        type_ = 'node-requests'

    filterable_fields = frozenset([
        'creator',
        'request_type',
        'machine_state',
        'created',
        'id',
        'target',
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
        source='creator___id',
    )

    links = LinksField({
        'self': 'get_absolute_url',
        'target': 'get_target_url',
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
        source='target__guids___id',
    )

    requested_permissions = ser.ChoiceField(
        help_text='These are supposed to represent the default permission suggested when the Node admin sees users '
                  'listed in an `Request Access` list.',
        choices=osf_permissions.API_CONTRIBUTOR_PERMISSIONS,
        required=False,
    )
    message_recipient = RelationshipField(
        help_text='An optional user who will recieve a message probably an email exaplining the nature of the request.',
        required=False,
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user._id>'},
    )

    def get_target_url(self, obj):
        return absolute_reverse('nodes:node-detail', kwargs={'node_id': obj.target._id, 'version': self.context['request'].parser_context['kwargs']['version']})


class RegistrationRequestSerializer(RequestSerializer):
    class Meta:
        type_ = 'registration-requests'

    target = RelationshipField(
        read_only=True,
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<target._id>'},
        source='target__guids___id',
    )

    def get_target_url(self, obj):
        return absolute_reverse(
            'registrations:registration-detail', kwargs={
                'node_id': obj.target._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

from typing import Any, Dict, Optional
from django.db import IntegrityError
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.serializers import Serializer
from osf.models import Node, NodeRequest, Institution, OSFUser
from osf.utils.workflows import DefaultStates, NodeRequestTypes
from website import settings
from website.mails import send_mail, NODE_REQUEST_INSTITUTIONAL_ACCESS_REQUEST
from api.base.exceptions import Conflict
from api.base.utils import get_user_auth


class NodeRequestCreateSerializer(Serializer):
    def create(self, validated_data: Dict[str, Any]) -> NodeRequest:
        auth = get_user_auth(self.context['request'])
        if not auth.user:
            raise PermissionDenied('Authentication required.')

        try:
            node = self.context['view'].get_target()
        except PermissionDenied:
            node = self.context['view'].get_target(check_object_permissions=False)
            if auth.user in node.contributors:
                raise PermissionDenied('You cannot request access to a node you contribute to.')
            raise

        request_type = validated_data.get('request_type')
        if not request_type:
            raise ValidationError('You must specify a valid request_type.')

        match request_type:
            case NodeRequestTypes.ACCESS.value:
                return self.make_node_access_request(node, validated_data)
            case NodeRequestTypes.INSTITUTIONAL_REQUEST.value:
                return self.make_node_institutional_access_request(node, validated_data)
            case _:
                raise NotImplementedError(f'Request type "{request_type}" not implemented.')

    def make_node_access_request(self, node: Node, validated_data: Dict[str, Any]) -> NodeRequest:
        return self._create_node_request(node, validated_data)

    def make_node_institutional_access_request(self, node: Node, validated_data: Dict[str, Any]) -> NodeRequest:
        node_request = self._create_node_request(node, validated_data)
        sender = self.context['request'].user
        message_recipient_id = validated_data.get('message_recipient')
        institution_id = validated_data.get('institution')

        message_recipient: Optional[OSFUser] = OSFUser.load(message_recipient_id) if message_recipient_id else None
        institution: Institution = Institution.objects.get(_id=institution_id)

        if message_recipient:
            if not message_recipient.is_affiliated_with_institution(institution):
                raise PermissionDenied(f"User {message_recipient._id} is not affiliated with the institution.")

            send_mail(
                to_addr=message_recipient.username,
                mail=NODE_REQUEST_INSTITUTIONAL_ACCESS_REQUEST,
                user=message_recipient,
                sender=sender,
                recipient=message_recipient,
                comment=validated_data['comment'],
                institution=institution,
                osf_url=settings.DOMAIN,
                node=node_request.target,
            )

        return node_request

    def _create_node_request(self, node: Node, validated_data: Dict[str, Any]) -> NodeRequest:
        creator = self.context['request'].user
        request_type = validated_data['request_type']
        comment = validated_data.get('comment', '')
        requested_permissions = validated_data.get('requested_permissions')
        message_recipient_id = validated_data.get('message_recipient')
        message_recipient = OSFUser.load(message_recipient_id) if message_recipient_id else None

        try:
            node_request = NodeRequest.objects.create(
                target=node,
                creator=creator,
                comment=comment,
                machine_state=DefaultStates.INITIAL.value,
                request_type=request_type,
                requested_permissions=requested_permissions,
                message_recipient=message_recipient,
            )
            node_request.save()
        except IntegrityError:
            raise Conflict(f"Users may not have more than one '{request_type}' request per node.")

        node_request.run_submit(creator)
        return node_request


class PreprintRequestSerializer(RequestSerializer):
    class Meta:
        type_ = 'preprint-requests'

    target = RelationshipField(
        read_only=True,
        related_view='preprints:preprint-detail',
        related_view_kwargs={'preprint_id': '<target._id>'},
        source='target__guids___id',
    )

    actions = RelationshipField(
        read_only=True,
        related_view='requests:request-action-list',
        related_view_kwargs={'request_id': '<_id>'},
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
            raise Conflict(f'Users may not have more than one {request_type} request per preprint.')

        if request_type != RequestTypes.WITHDRAWAL.value:
            raise exceptions.ValidationError('You must specify a valid request_type.')

        preprint_request = PreprintRequest.objects.create(
            target=preprint,
            creator=auth.user,
            comment=comment,
            machine_state=DefaultStates.INITIAL.value,
            request_type=request_type,
        )
        preprint_request.save()
        preprint_request.run_submit(auth.user)
        return preprint_request
