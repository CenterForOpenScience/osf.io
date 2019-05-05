
from rest_framework import generics, permissions as drf_permissions
from django.db.models import Q

from api.base import permissions as base_permissions
from api.base.filters import ListFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.base.versioning import PrivateVersioning
from api.meetings.serializers import MeetingSerializer, MeetingSubmissionSerializer
from api.meetings.permissions import IsPublic

from framework.auth.oauth_scopes import CoreScopes

from osf.models import AbstractNode, Conference
from website import settings

class MeetingMixin(object):
    """Mixin with convenience method get_meeting
    """

    meeting_lookup_url_kwarg = 'meeting_id'

    def get_meeting(self):
        meeting = get_object_or_error(
            Conference,
            Q(endpoint=self.kwargs[self.meeting_lookup_url_kwarg]),
            self.request,
            display_name='meeting',
        )
        # caching num_submissions on the Conference object
        meeting.num_submissions = meeting.submissions.count()
        meeting.save()
        return meeting


class MeetingList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/meetings_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.MEETINGS_READ]
    required_write_scopes = [CoreScopes.NULL]
    model = Conference

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning

    serializer_class = MeetingSerializer
    view_category = 'meetings'
    view_name = 'meeting-list'

    ordering = ('-modified', )  # default ordering

    # overrides ListFilterMixin
    def get_default_queryset(self):
        conferences = Conference.objects.filter(is_meeting=True)
        for conference in conferences:
            # caching num_submissions on the Conference objects
            conference.num_submissions = conference.submissions.count()
            conference.save()
        return conferences.filter(num_submissions__gte=settings.CONFERENCE_MIN_COUNT)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class MeetingDetail(JSONAPIBaseView, generics.RetrieveAPIView, MeetingMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/meetings_detail).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.MEETINGS_READ]
    required_write_scopes = [CoreScopes.NULL]
    model = Conference

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning

    serializer_class = MeetingSerializer
    view_category = 'meetings'
    view_name = 'meeting-detail'

    def get_object(self):
        # No minimum submissions count for accessing meeting directly
        return self.get_meeting()


class MeetingSubmissionList(JSONAPIBaseView, generics.ListAPIView, MeetingMixin, ListFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/meetings_submission_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsPublic,
    )

    required_read_scopes = [CoreScopes.MEETINGS_READ, CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]
    model = AbstractNode

    # This view goes under the _/ namespace
    versioning_class = PrivateVersioning

    serializer_class = MeetingSubmissionSerializer
    view_category = 'meetings'
    view_name = 'meeting-submissions'

    ordering = ('-modified', )  # default ordering

    def get_serializer_context(self):
        context = super(MeetingSubmissionList, self).get_serializer_context()
        context['meeting'] = self.get_meeting()
        return context

    # overrides ListFilterMixin
    def get_default_queryset(self):
        return self.get_meeting().submissions

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()
