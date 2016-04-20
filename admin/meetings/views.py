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


class MeetingFormView(GuidFormView):
    template_name = 'meetings/detail.html'


class MeetingCreateFormView(FormView):
    template_name = 'meetings/create.html'
