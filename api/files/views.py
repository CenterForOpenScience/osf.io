from django.db.models import Max

from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound

from framework.auth.oauth_scopes import CoreScopes

from osf.models import (
    Guid,
    BaseFileNode,
    FileVersion,
    CedarMetadataRecord,
)

from api.base.exceptions import Gone
from api.base.filters import ListFilterMixin
from api.base.permissions import PermissionWithGetter
from api.base.throttling import CreateGuidThrottle, NonCookieAuthThrottle, UserRateThrottle, BurstRateThrottle
from api.base import utils
from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from api.cedar_metadata_records.serializers import CedarMetadataRecordsListSerializer
from api.cedar_metadata_records.utils import can_view_record
from api.nodes.permissions import ContributorOrPublic
from api.files import annotations
from api.files.permissions import IsPreprintFile, CheckedOutOrAdmin
from api.files.serializers import (
    FileSerializer,
    FileDetailSerializer,
    FileVersionSerializer,
)


class FileMixin:
    """Mixin with convenience methods for retrieving the current file based on the
    current URL. By default, fetches the file based on the file_id kwarg.
    """

    serializer_class = FileSerializer
    file_lookup_url_kwarg = 'file_id'

    def get_file(self, check_permissions=True):
        try:
            obj = utils.get_object_or_error(BaseFileNode, self.kwargs[self.file_lookup_url_kwarg], self.request, display_name='file')
        except NotFound:
            obj = utils.get_object_or_error(Guid, self.kwargs[self.file_lookup_url_kwarg], self.request).referent
            if not isinstance(obj, BaseFileNode):
                raise NotFound
            if obj.is_deleted:
                raise Gone(detail='The requested file is no longer available.')

        if getattr(obj.target, 'deleted', None):
            raise Gone(detail='The requested file is no longer available.', meta={'flagged_content': getattr(obj.target, 'is_spammy', False)})

        if getattr(obj.target, 'is_retracted', False):
            raise Gone(detail='The requested file is no longer available.')

        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
        return obj


class FileDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, FileMixin):
    """See [documentation for this endpoint](https://developer.osf.io/#operation/files_detail).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        IsPreprintFile,
        CheckedOutOrAdmin,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, 'target'),
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = FileDetailSerializer
    throttle_classes = (CreateGuidThrottle, NonCookieAuthThrottle, UserRateThrottle, BurstRateThrottle)
    view_category = 'files'
    view_name = 'file-detail'

    def get_target(self):
        return self.get_file().target

    # overrides RetrieveAPIView
    def get_object(self):
        file = self.get_file()

        if self.request.GET.get('create_guid', False):
            auth = utils.get_user_auth(self.request)
            if self.get_target().can_view(auth):
                file.get_guid(create=True)

        # We normally would pass this through `get_file` as an annotation, but the `select_for_update` feature prevents
        # grouping versions in an annotation
        if file.kind == 'file':
            file.show_as_unviewed = annotations.check_show_as_unviewed(
                user=self.request.user, osf_file=file,
            )
            if file.provider == 'osfstorage':
                file.date_modified = file.versions.aggregate(Max('created'))['created__max']
            else:
                file.date_modified = file.history[-1]['modified']

        return file


class FileVersionsList(JSONAPIBaseView, generics.ListAPIView, FileMixin):
    """See [documentation for this endpoint](https://developer.osf.io/#operation/files_versions).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, 'target'),
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = FileVersionSerializer
    view_category = 'files'
    view_name = 'file-versions'

    ordering = ('-modified',)

    def get_queryset(self):
        self.file = self.get_file()
        return self.file.versions.all()

    def get_serializer_context(self):
        context = JSONAPIBaseView.get_serializer_context(self)
        context['file'] = self.file
        return context


def node_from_version(request, view, obj):
    return view.get_file(check_permissions=False).target


class FileVersionDetail(JSONAPIBaseView, generics.RetrieveAPIView, FileMixin):
    """See [documentation for this endpoint](https://developer.osf.io/#operation/files_version_detail).
    """
    version_lookup_url_kwarg = 'version_id'
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, node_from_version),
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = FileVersionSerializer
    view_category = 'files'
    view_name = 'version-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        self.file = self.get_file()
        maybe_version = self.file.get_version(self.kwargs[self.version_lookup_url_kwarg])

        # May raise a permission denied
        # Kinda hacky but versions have no reference to node or file
        self.check_object_permissions(self.request, self.file)
        return utils.get_object_or_error(FileVersion, getattr(maybe_version, '_id', ''), self.request)

    def get_serializer_context(self):
        context = JSONAPIBaseView.get_serializer_context(self)
        context['file'] = self.file
        return context


class FileCedarMetadataRecordsList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, FileMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PermissionWithGetter(ContributorOrPublic, 'target'),
    )
    required_read_scopes = [CoreScopes.CEDAR_METADATA_RECORD_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = CedarMetadataRecordsListSerializer

    view_category = 'files'
    view_name = 'file-cedar-metadata-records-list'

    def get_default_queryset(self):
        guid = self.get_file().get_guid()
        if not guid:
            return CedarMetadataRecord.objects.none()
        file_records = CedarMetadataRecord.objects.filter(guid___id=guid._id)
        user_auth = utils.get_user_auth(self.request)
        record_ids = [record.id for record in file_records if can_view_record(user_auth, record, guid_type=BaseFileNode)]
        return CedarMetadataRecord.objects.filter(pk__in=record_ids)

    def get_queryset(self):
        return self.get_queryset_from_request()

from website import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from framework.auth import Auth
from osf import features
from waffle import flag_is_active
from api.base import permissions as base_permissions
from addons.base import views as request_helpers

def _decrypt_and_decode_jwt_payload(payload):
    try:
        payload_encrypted = payload.encode('utf-8')
        payload_decrypted = jwe.decrypt(payload_encrypted, request_helpers.WATERBUTLER_JWE_KEY)
        from website import settings
        return jwt.decode(
            payload_decrypted,
            settings.WATERBUTLER_JWT_SECRET,
            options={'require_exp': True},
            algorithms=[settings.WATERBUTLER_JWT_ALGORITHM],
        )['data']
    except (jwt.InvalidTokenError, KeyError) as err:
        raise err

class WaterbutlerAuthView(APIView):
    """
    Authenticate a request and construct a JWT payload for Waterbutler callbacks.
    """

    def get(self, request, *args, **kwargs):

        print('*' * 100)
        auth = Auth(user=request.user)
        # Decode incoming WB payload
        waterbutler_data = _decrypt_and_decode_jwt_payload(request.GET['payload'])
        # Resolve target resource
        resource = request_helpers._get_authenticated_resource(
            waterbutler_data['nid'],
        )
        # action = waterbutler_data['action']
        # Validate permissions

        # request_helpers._check_resource_permissions(
        #     resource=resource,
        #     auth=auth,
        #     action=action,
        # )
        provider_name = waterbutler_data['provider']
        file_version = None
        file_node = None
        # osfstorage / legacy flow
        if (
            provider_name == 'osfstorage'
            or not flag_is_active(request, features.ENABLE_GV)
        ):
            file_version, file_node = (
                request_helpers._get_osfstorage_file_version_and_node(
                    file_path=waterbutler_data.get('path'),
                    file_version_id=waterbutler_data.get('version'),
                )
            )
            (
                waterbutler_settings,
                waterbutler_credentials,
            ) = request_helpers._get_waterbutler_configs(
                resource=resource,
                provider_name=provider_name,
                file_version=file_version,
            )
        # GV provider flow
        else:
            result = request_helpers.get_waterbutler_config(
                gv_addon_pk=(
                    f"{waterbutler_data['nid']}:"
                    f"{waterbutler_data['provider']}"
                ),
                requested_resource=resource,
                requesting_user=auth.user,
                addon_type='configured-storage-addons',
            )
            if not result:
                return Response(
                    {
                        'detail': (
                            'Requested Provider is not configured '
                            'for given node'
                        ),
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            waterbutler_settings = result.get_attribute('config')
            waterbutler_credentials = result.get_attribute('credentials')
        # Metrics/logging
        # request_helpers._enqueue_metrics(
        #     file_version=file_version,
        #     file_node=file_node,
        #     action=action,
        #     auth=auth,
        #     from_mfr=request_helpers._download_is_from_mfr(waterbutler_data),
        # )
        # Construct WB response payload
        payload = _construct_payload(
            auth=auth,
            resource=resource,
            credentials=waterbutler_credentials,
            waterbutler_settings=waterbutler_settings,
        )

        return Response(payload, status=status.HTTP_200_OK)

from osf.models import Registration
from django.utils import timezone
import datetime
import jwe
import jwt

def _construct_payload(auth, resource, credentials, waterbutler_settings):

    if isinstance(resource, Registration):
        callback_url = resource.callbacks_url
    else:
        callback_url = f'http://localhost:8000/v2/files/project/{resource._primary_key}/waterbutler/logs/'
        # callback_url = resource.api_url_for(
        #     'create_waterbutler_log',
        #     _absolute=True,
        #     _internal=True
        # )

    # Construct the data dictionary for JWT encoding
    from website import settings
    jwt_data = {
        'exp': timezone.now() + datetime.timedelta(seconds=settings.WATERBUTLER_JWT_EXPIRATION),
        'data': {
            'auth': request_helpers.make_auth(auth.user),
            'credentials': credentials,
            'settings': waterbutler_settings,
            'callback_url': callback_url,
        },
    }

    # JWT encode the data
    encoded_jwt = jwt.encode(
        jwt_data,
        settings.WATERBUTLER_JWT_SECRET,
        algorithm=settings.WATERBUTLER_JWT_ALGORITHM,
    )

    # Encrypt the encoded JWT with JWE
    decoded_encrypted_jwt = jwe.encrypt(
        encoded_jwt.encode(),
        request_helpers.WATERBUTLER_JWE_KEY,
    ).decode()

    return {'payload': decoded_encrypted_jwt}

import os
from django.db import transaction

from rest_framework.views import APIView

from framework.exceptions import HTTPError
import copy
from api.base.parsers import HMACSignedParser
from website.project.decorators import _inject_nodes
class WaterbutlerLogView(APIView):

    parser_classes = [HMACSignedParser]

    authentication_classes = []
    permission_classes = []

    def put(self, request, *args, **kwargs):
        payload = copy.deepcopy(request.data)

        try:
            if request_helpers.Preprint.load(kwargs.get('pid')):
                _inject_nodes(kwargs)

            _inject_nodes(kwargs)

            if getattr(kwargs['node'], 'is_collection', True):
                raise HTTPError(
                    404,
                )

            result = self._create_waterbutler_log(
                payload=payload,
                **kwargs,
            )

            return Response(result, status=status.HTTP_200_OK)

        except HTTPError as exc:
            return Response(
                {'detail': str(exc)},
                status=getattr(exc, 'code', 400),
            )

    def _create_waterbutler_log(self, payload, **kwargs):

        with transaction.atomic():

            try:
                auth_data = payload['auth']

                # Don't log download actions
                if payload['action'] in request_helpers.DOWNLOAD_ACTIONS:
                    guid_id = payload['metadata'].get('nid')

                    node, _ = Guid.load_referent(guid_id)

                    return {'status': 'success'}

                user = request_helpers.OSFUser.load(auth_data['id'])

                if user is None:
                    raise HTTPError(status.HTTP_400_BAD_REQUEST)

                action = request_helpers.LOG_ACTION_MAP[payload['action']]

            except KeyError:
                raise HTTPError(status.HTTP_400_BAD_REQUEST)

            auth = Auth(user=user)

            node = (
                kwargs.get('node')
                or kwargs.get('project')
                or request_helpers.Preprint.load(kwargs.get('nid'))
                or request_helpers.Preprint.load(kwargs.get('pid'))
            )

            #
            # MOVE / COPY FLOW
            #
            if action in (
                request_helpers.NodeLog.FILE_MOVED,
                request_helpers.NodeLog.FILE_COPIED,
            ):

                for bundle in ('source', 'destination'):
                    for key in (
                        'provider',
                        'materialized',
                        'name',
                        'nid',
                    ):
                        if key not in payload[bundle]:
                            raise HTTPError(
                                status.HTTP_400_BAD_REQUEST,
                            )

                dest = payload['destination']
                src = payload['source']

                #
                # Detect rename
                #
                if src is not None and dest is not None:

                    dest_path = dest['materialized']
                    src_path = src['materialized']

                    if (
                        dest_path.endswith('/')
                        and src_path.endswith('/')
                    ):
                        dest_path = os.path.dirname(dest_path)
                        src_path = os.path.dirname(src_path)

                    if (
                        os.path.split(dest_path)[0]
                        == os.path.split(src_path)[0]
                        and dest['provider'] == src['provider']
                        and dest['nid'] == src['nid']
                        and dest['name'] != src['name']
                    ):
                        action = request_helpers.LOG_ACTION_MAP['rename']

                destination_node = node
                source_node = (
                    request_helpers.AbstractNode.load(src['nid'])
                    or request_helpers.Preprint.load(src['nid'])
                )

                #
                # Resolve addons
                #
                source = None
                if hasattr(source_node, 'get_addon'):
                    source = source_node.get_addon(
                        payload['source']['provider'],
                    )

                destination = None
                if hasattr(node, 'get_addon'):
                    destination = node.get_addon(
                        payload['destination']['provider'],
                    )

                #
                # Enrich source payload
                #
                payload['source'].update({
                    'materialized': payload['source'][
                        'materialized'
                    ].lstrip('/'),

                    'addon': (
                        source.config.full_name
                        if source else 'osfstorage'
                    ),

                    'url': source_node.web_url_for(
                        'addon_view_or_download_file',
                        path=payload['source']['path'].lstrip('/'),
                        provider=payload['source']['provider'],
                    ),

                    'node': {
                        '_id': source_node._id,
                        'url': source_node.url,
                        'title': source_node.title,
                    },
                })

                #
                # Enrich destination payload
                #
                payload['destination'].update({
                    'materialized': payload['destination'][
                        'materialized'
                    ].lstrip('/'),

                    'addon': (
                        destination.config.full_name
                        if destination else 'osfstorage'
                    ),

                    'url': destination_node.web_url_for(
                        'addon_view_or_download_file',
                        path=payload['destination'][
                            'path'
                        ].lstrip('/'),
                        provider=payload['destination'][
                            'provider'
                        ],
                    ),

                    'node': {
                        '_id': destination_node._id,
                        'url': destination_node.url,
                        'title': destination_node.title,
                    },
                })

                #
                # Create log
                #
                if not payload.get('errors'):
                    destination_node.add_log(
                        action=action,
                        auth=auth,
                        params=payload,
                    )

                #
                # Notifications
                #
                if (
                    payload.get('email')
                    or payload.get('errors')
                ):

                    if payload.get('email'):
                        notification_type = (
                            request_helpers.NotificationTypeEnum
                            .USER_FILE_OPERATION_SUCCESS
                            .instance
                        )

                    if payload.get('errors'):
                        notification_type = (
                            request_helpers.NotificationTypeEnum
                            .USER_FILE_OPERATION_FAILED
                            .instance
                        )

                    notification_type.emit(
                        user=user,
                        subscribed_object=node,
                        event_context={
                            'action': payload['action'],
                            'source_node': source_node._id,
                            'source_node_title': source_node.title,
                            'destination_node':
                                destination_node._id,
                            'destination_node_title':
                                destination_node.title,
                            'destination_node_parent_node_title': (
                                destination_node
                                .parent_node.title
                                if destination_node.parent_node
                                else None
                            ),
                            'source_path': payload['source'][
                                'materialized'
                            ],
                            'source_addon':
                                payload['source']['addon'],
                            'destination_addon':
                                payload['destination']['addon'],
                            'osf_support_email':
                                settings.OSF_SUPPORT_EMAIL,
                            'logo':
                                settings.OSF_LOGO,
                            'OSF_LOGO_LIST':
                                settings.OSF_LOGO_LIST,
                            'OSF_LOGO':
                                settings.OSF_LOGO,
                            'domain':
                                settings.DOMAIN,
                        },
                    )

                #
                # Operation failed
                #
                if payload.get('errors'):
                    return {'status': 'success'}

            #
            # NORMAL FLOW
            #
            else:
                node.create_waterbutler_log(
                    auth=auth,
                    action=action,
                    payload=payload,
                )

        #
        # Update storage metrics
        #
        metadata = (
            payload.get('metadata')
            or payload.get('destination')
        )

        target_node = request_helpers.AbstractNode.load(
            metadata.get('nid'),
        )

        if (
            target_node
            and payload['action'] != 'download_file'
        ):
            request_helpers.update_storage_usage_with_size(payload)

        #
        # Fire signals
        #
        with transaction.atomic():
            request_helpers.file_signals.file_updated.send(
                target=node,
                user=user,
                event_type=action,
                payload=payload,
            )

        return {'status': 'success'}
