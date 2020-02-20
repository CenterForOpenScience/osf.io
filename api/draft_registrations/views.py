from api.nodes.serializers import DraftRegistrationDetailSerializer
from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from api.base.exceptions import Gone
from api.nodes.permissions import IsAdminContributor
from rest_framework import generics, permissions as drf_permissions
from framework.auth.oauth_scopes import CoreScopes
from api.base.utils import get_object_or_error
from osf.models import DraftRegistration
from rest_framework.exceptions import PermissionDenied


class DraftRegistrationDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_draft_registrations_read).
    """
    permission_classes = (
        IsAdminContributor,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_WRITE]

    serializer_class = DraftRegistrationDetailSerializer
    view_category = 'draft_registrations'
    view_name = 'draft-registration-detail'

    def get_object(self):
        draft_id = self.kwargs['draft_id']
        draft = get_object_or_error(DraftRegistration, draft_id, self.request)

        if self.request.method not in drf_permissions.SAFE_METHODS:
            registered_and_deleted = draft.registered_node and draft.registered_node.is_deleted

            if draft.registered_node and not draft.registered_node.is_deleted:
                raise PermissionDenied('This draft has already been registered and cannot be modified.')

            if draft.is_pending_review:
                raise PermissionDenied('This draft is pending review and cannot be modified.')

            if draft.requires_approval and draft.is_approved and (not registered_and_deleted):
                raise PermissionDenied('This draft has already been approved and cannot be modified.')
        else:
            if draft.registered_node and not draft.registered_node.is_deleted:
                raise Gone(detail='This draft has already been registered.')

        self.check_object_permissions(self.request, draft.branched_from)
        return draft
