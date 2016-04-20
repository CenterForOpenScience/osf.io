from __future__ import unicode_literals

from django.views.generic import ListView, FormView
from django.views.defaults import page_not_found
from modularodm import Q

from website.models import Conference
from admin.base.views import GuidFormView, GuidView

from admin.meetings.forms import MeetingForm
from admin.meetings.serializers import serialize_meeting


class MeetingListView(ListView):
    template_name = 'meetings/create.html'
    paginate_by = 10
    paginate_orphans = 1
    context_object_name = 'meeting'

    def get_queryset(self):
        return Conference.find()

    def get_context_data(self, **kwargs):
        queryset = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(queryset)
        paginator, page, queryset, is_paginated = self.paginate_queryset(
            queryset, page_size
        )
        kwargs.setdefault('meetings', map(serialize_meeting, queryset))
        kwargs.setdefault('page', page)
        return super(MeetingListView, self).get_context_data(**kwargs)


class MeetingFormView(GuidFormView):
    template_name = 'meetings/detail.html'
    form_class = MeetingForm

    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass

    def get_initial(self):
        self.initial = serialize_meeting(
            Conference.load(self.kwargs.get('guid'))
        )
        return super(MeetingFormView, self).get_initial()

    def form_valid(self, form):
        pass

    @property
    def success_url(self):
        return None


class MeetingCreateFormView(FormView):
    template_name = 'meetings/create.html'
    form_class = MeetingForm

    def get(self, request, *args, **kwargs):
        pass

    def post(self, request, *args, **kwargs):
        pass

    def form_valid(self, form):
        # Validation already catches if a conference endpoint exists
        pass

    def get_success_url(self):
        pass
