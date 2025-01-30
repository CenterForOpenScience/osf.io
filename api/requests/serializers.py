from django.db import IntegrityError, transaction
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

from rest_framework.exceptions import PermissionDenied, ValidationError


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
    request_type = ser.ChoiceField(read_only=True, required=False, choices=NodeRequestTypes.choices())

    class Meta:
        type_ = 'node-requests'

    target = RelationshipField(
        read_only=True,
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<target._id>'},
        source='target__guids___id',
    )

    requested_permissions = ser.ChoiceField(
        help_text='These are the default permission suggested when the Node admin sees users '
                  'listed in an `Request Access` list.',
        choices=osf_permissions.API_CONTRIBUTOR_PERMISSIONS,
        required=False,
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


class NodeRequestCreateSerializer(NodeRequestSerializer):
    request_type = ser.ChoiceField(read_only=False, required=False, choices=NodeRequestTypes.choices())
    message_recipient = RelationshipField(
        help_text='An optional user who will receive an email explaining the nature of the request.',
        required=False,
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user._id>'},
    )
    bcc_sender = ser.BooleanField(
        required=False,
        default=False,
        help_text='If true, BCCs the sender, giving them a copy of the email message they sent.',
    )
    reply_to = ser.BooleanField(
        default=False,
        help_text='Whether to set the sender\'s username as the `Reply-To` header in the email.',
    )

    def to_internal_value(self, data):
        """
        Retrieves the id value from `RelationshipField` fields
        """
        institution_id = data.pop('institution', None)
        message_recipient_id = data.pop('message_recipient', None)
        data = super().to_internal_value(data)

        if institution_id:
            data['institution'] = institution_id

        if message_recipient_id:
            data['message_recipient'] = message_recipient_id
        return data

    def get_node_and_validate_non_contributor(self, auth):
        """
        Ensures request user isn't already a contributor.
        """
        try:
            return self.context['view'].get_target()
        except exceptions.PermissionDenied:
            node = self.context['view'].get_target(check_object_permissions=False)
            if auth.user in node.contributors:
                raise exceptions.PermissionDenied('You cannot request access to a node you contribute to.')
            raise

    def create(self, validated_data) -> NodeRequest:
        auth = get_user_auth(self.context['request'])
        if not auth.user:
            raise exceptions.PermissionDenied

        node = self.get_node_and_validate_non_contributor(auth)

        request_type = validated_data.get('request_type')
        match request_type:
            case NodeRequestTypes.ACCESS.value:
                return self._create_node_request(node, validated_data)
            case NodeRequestTypes.INSTITUTIONAL_REQUEST.value:
                return self.make_node_institutional_access_request(node, validated_data)
            case _:
                raise ValidationError('You must specify a valid request_type.')

    def make_node_institutional_access_request(self, node, validated_data) -> NodeRequest:
        sender = self.context['request'].user
        node_request = self._create_node_request(node, validated_data)
        node_request.is_institutional_request = True
        node_request.save()
        institution = Institution.objects.get(_id=validated_data['institution'])
        recipient = OSFUser.load(validated_data.get('message_recipient'))

        if recipient:
            if not recipient.is_affiliated_with_institution(institution):
                raise PermissionDenied(f"User {recipient._id} is not affiliated with the institution.")

            if validated_data['comment']:
                send_mail(
                    to_addr=recipient.username,
                    mail=NODE_REQUEST_INSTITUTIONAL_ACCESS_REQUEST,
                    user=recipient,
                    sender=sender,
                    bcc_addr=[sender.username] if validated_data['bcc_sender'] else None,
                    reply_to=sender.username if validated_data['reply_to'] else None,
                    recipient=recipient,
                    comment=validated_data['comment'],
                    institution=institution,
                    osf_url=settings.DOMAIN,
                    node=node_request.target,
                )

        return node_request

    def _create_node_request(self, node, validated_data) -> NodeRequest:
        creator = self.context['request'].user
        request_type = validated_data['request_type']
        comment = validated_data.get('comment', '')
        requested_permissions = validated_data.get('requested_permissions')
        try:
            with transaction.atomic():
                node_request = NodeRequest.objects.create(
                    target=node,
                    creator=creator,
                    comment=comment,
                    machine_state=DefaultStates.INITIAL.value,
                    request_type=request_type,
                    requested_permissions=requested_permissions,
                )
                node_request.save()
        except IntegrityError:
            # if INSTITUTIONAL_REQUEST updates and restarts the request, transforms basic assess to institutional
            with transaction.atomic():
                if request_type != NodeRequestTypes.INSTITUTIONAL_REQUEST.value:
                    raise Conflict(f"Users may not have more than one {request_type} request per node.")

                node_request = NodeRequest.objects.get(
                    target=node,
                    creator=creator,
                )
                node_request.comment = comment
                node_request.machine_state = DefaultStates.INITIAL.value
                node_request.requested_permissions = requested_permissions
                node_request.request_type = request_type
                node_request.save()

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
