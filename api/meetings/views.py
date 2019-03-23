
from rest_framework import generics, permissions as drf_permissions


from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.meetings.serializers import MeetingSerializer
from api.nodes.permissions import ContributorOrPublic
from api.nodes.serializers import NodeSerializer

from framework.auth.oauth_scopes import CoreScopes

from osf.models import AbstractNode, Conference, Tag


class MeetingMixin(object):
    """Mixin with convenience method get_meeting
    """

    meeting_lookup_url_kwarg = 'meeting_id'

    def get_meeting(self):
        meeting = get_object_or_error(
            Conference,
            self.kwargs[self.meeting_lookup_url_kwarg],
            self.request,
            display_name='meeting',
        )
        return meeting

    def get_submissions(self):
        conference = self.get_meeting()
        tags = Tag.objects.filter(system=False, name__iexact=conference.endpoint).values_list('pk', flat=True)
        return AbstractNode.objects.filter(tags__in=tags, is_public=True, is_deleted=False)


class MeetingList(JSONAPIBaseView, generics.ListAPIView):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/meetings_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.MEETINGS_READ]
    required_write_scopes = [CoreScopes.NULL]
    model = Conference

    serializer_class = MeetingSerializer
    view_category = 'meetings'
    view_name = 'meeting-list'

    ordering = ('-modified', )  # default ordering

    def get_queryset(self):
        return Conference.objects.filter(is_meeting=True)


class MeetingDetail(JSONAPIBaseView, generics.RetrieveAPIView, MeetingMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/meetings_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.MEETINGS_READ]
    required_write_scopes = [CoreScopes.NULL]
    model = Conference

    serializer_class = MeetingSerializer
    view_category = 'meetings'
    view_name = 'meeting-list'

    ordering = ('-modified', )  # default ordering

    def get_object(self):
        return self.get_meeting()


class MeetingSubmissionList(JSONAPIBaseView, generics.ListAPIView, MeetingMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/meetings_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
    )

    required_read_scopes = [CoreScopes.MEETINGS_READ, CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]
    model = Conference

    serializer_class = NodeSerializer
    view_category = 'meetings'
    view_name = 'meeting-submissions'

    ordering = ('-modified', )  # default ordering

    def get_queryset(self):
        return self.get_submissions()
