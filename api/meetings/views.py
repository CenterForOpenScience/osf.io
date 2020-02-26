
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound
from django.db.models import Q, Count, Subquery, OuterRef, Case, When, Value, CharField, F
from django.db.models.functions import Coalesce
from django.contrib.contenttypes.models import ContentType

from addons.osfstorage.models import OsfStorageFile
from api.base import permissions as base_permissions
from api.base.exceptions import InvalidFilterOperator
from api.base.filters import ListFilterMixin

from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.base.versioning import PrivateVersioning
from api.meetings.serializers import MeetingSerializer, MeetingSubmissionSerializer
from api.meetings.permissions import IsPublic
from api.nodes.views import NodeMixin

from framework.auth.oauth_scopes import CoreScopes

from osf.models import AbstractNode, Conference, Contributor, Tag, PageCounter
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

    ordering_fields = ('name', 'submissions_count', 'location', 'start_date',)

    # overrides ListFilterMixin
    def get_default_queryset(self):
        conferences = Conference.objects.filter(
            is_meeting=True,
            submissions__is_public=True,
            submissions__is_deleted=False,
        ).annotate(
            submissions_count=Count(F('submissions')),
        )
        return conferences.filter(submissions_count__gte=settings.CONFERENCE_MIN_COUNT)

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

    ordering = ('-created', )  # default ordering
    ordering_fields = ('title', 'meeting_category', 'author_name', 'created', 'download_count',)

    # overrides ListFilterMixin
    def get_default_queryset(self):
        meeting = self.get_meeting()
        return self.annotate_queryset_for_filtering_and_sorting(meeting, meeting.valid_submissions)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()

    def build_query_from_field(self, field_name, operation):
        if field_name == 'author_name':
            if operation['op'] != 'eq':
                raise InvalidFilterOperator(value=operation['op'], valid_operators=['eq'])
            return Q(author_name__icontains=operation['value'])

        if field_name == 'meeting_category':
            if operation['op'] != 'eq':
                raise InvalidFilterOperator(value=operation['op'], valid_operators=['eq'])
            return Q(meeting_category__icontains=operation['value'])

        return super(MeetingSubmissionList, self).build_query_from_field(field_name, operation)

    def annotate_queryset_for_filtering_and_sorting(self, meeting, queryset):
        queryset = self.annotate_queryset_with_meeting_category(meeting, queryset)
        queryset = self.annotate_queryset_with_author_name(queryset)
        queryset = self.annotate_queryset_with_download_count(queryset)
        return queryset

    def annotate_queryset_with_meeting_category(self, meeting, queryset):
        """
        Annotates queryset with meeting_category - if submission1 tag exists, use this,
        otherwise assume default submission2 tag
        """
        # Setup meeting category subquery (really existence of certain tags)
        category_1 = meeting.field_names.get('submission1', 'poster')
        category_2 = meeting.field_names.get('submission2', 'talk')
        tag_subquery = Tag.objects.filter(
            abstractnode_tagged=OuterRef('pk'),
            name=category_1,
        ).values_list('name', flat=True)

        queryset = queryset.annotate(cat_one_count=Count(Subquery(tag_subquery))).annotate(
            meeting_category=Case(
                When(cat_one_count=1, then=Value(category_1)),
                default=Value(category_2),
                output_field=CharField(),
            ),
        )
        return queryset

    def annotate_queryset_with_author_name(self, queryset):
        """
        Annotates queryset with author_name_category - it is the family_name if it exists, otherwise,
        the fullname is used
        """
        # Setup author name subquery (really first bibliographic contributor)
        contributors = Contributor.objects.filter(
            visible=True,
            node_id=OuterRef('pk'),
        ).order_by('_order')

        queryset = queryset.annotate(
            author_family_name=Subquery(contributors.values(('user__family_name'))[:1]),
            author_full_name=Subquery(contributors.values(('user__fullname'))[:1]),
            author_id=Subquery(contributors.values(('user__guids___id'))[:1]),
        ).annotate(
            author_name=Case(
                When(author_family_name='', then=F('author_full_name')),
                default=F('author_family_name'),
                output_field=CharField(),
            ),
        )
        return queryset

    def annotate_queryset_with_download_count(self, queryset):
        """
        Annotates queryset with download count of first osfstorage file
        """
        pages = PageCounter.objects.filter(
            action='download',
            resource_id=OuterRef('guids__id'),
            file_id=OuterRef('file_id'),
            version=None,
        )

        file_subqs = OsfStorageFile.objects.filter(
            target_content_type_id=ContentType.objects.get_for_model(AbstractNode),
            target_object_id=OuterRef('pk'),
        ).order_by('created')

        queryset = queryset.annotate(file_id=Subquery(file_subqs.values('id')[:1])).annotate(
            download_count=Coalesce(Subquery(pages.values('total')[:1]), Value(0)),
        )
        return queryset


class MeetingSubmissionDetail(BaseMeetingSubmission, generics.RetrieveAPIView, NodeMixin):
    view_name = 'meeting-submission-detail'

    serializer_class = MeetingSubmissionSerializer
    node_lookup_url_kwarg = 'submission_id'

    def get_object(self):
        meeting = self.get_meeting()
        node = self.get_node()
        # Submission must be associated with the Conference
        if node.id not in meeting.submissions.values_list('id', flat=True):
            raise NotFound('This is not a submission to {}.'.format(meeting.name))
        return node
