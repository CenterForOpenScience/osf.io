
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound
from django.db.models import Q, Count

from api.base import permissions as base_permissions
from api.base.filters import ListFilterMixin
from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.base.versioning import PrivateVersioning
from api.meetings.serializers import MeetingSerializer, MeetingSubmissionSerializer
from api.meetings.permissions import IsPublic
from api.nodes.views import NodeMixin

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


class BaseMeetingView(JSONAPIBaseView, MeetingMixin):
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


class MeetingList(BaseMeetingView, generics.ListAPIView, ListFilterMixin):

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


class MeetingDetail(BaseMeetingView, generics.RetrieveAPIView):

    view_name = 'meeting-detail'

    def get_object(self):
        # No minimum submissions count for accessing meeting directly
        return self.get_meeting()


class BaseMeetingSubmission(JSONAPIBaseView, MeetingMixin):
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

    def get_serializer_context(self):
        context = super(BaseMeetingSubmission, self).get_serializer_context()
        context['meeting'] = self.get_meeting()
        return context


class MeetingSubmissionList(BaseMeetingSubmission, generics.ListAPIView, ListFilterMixin):
    view_name = 'meeting-submissions'

    ordering = ('-modified', )  # default ordering

    # overrides ListFilterMixin
    def get_default_queryset(self):
        # Returning public meeting submissions that have at least one file attached
        return self.get_meeting().submissions.filter(
            files__type='osf.osfstoragefile',
            files__deleted_on__isnull=True,
        ).annotate(annotated_file_count=Count('files')).filter(annotated_file_count__gte=1)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class MeetingSubmissionDetail(BaseMeetingSubmission, generics.RetrieveAPIView, NodeMixin):
    view_name = 'meeting-submission-detail'

    serializer_class = MeetingSubmissionSerializer
    node_lookup_url_kwarg = 'submission_id'

    def get_object(self):
        meeting = self.get_meeting()
        node = self.get_node()
        # Submission must be associated with the Conference
        if node._id not in meeting.submissions.values_list('guids___id', flat=True):
            raise NotFound('This is not a submission to {}.'.format(meeting.name))
        return node
