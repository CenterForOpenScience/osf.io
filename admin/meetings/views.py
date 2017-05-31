from __future__ import unicode_literals
from copy import deepcopy

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, FormView
from django.core.urlresolvers import reverse
from django.http import Http404

from framework.auth.core import get_user
from osf.models.conference import Conference, DEFAULT_FIELD_NAMES
from website.conferences.exceptions import ConferenceError

from admin.meetings.forms import MeetingForm
from admin.meetings.serializers import serialize_meeting


class MeetingListView(PermissionRequiredMixin, ListView):
    template_name = 'meetings/list.html'
    paginate_by = 10
    paginate_orphans = 1
    context_object_name = 'meeting'
    permission_required = 'osf.view_conference'
    raise_exception = True

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


class MeetingFormView(PermissionRequiredMixin, FormView):
    template_name = 'meetings/detail.html'
    form_class = MeetingForm
    permission_required = 'osf.change_conference'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        endpoint = kwargs.get('endpoint')
        try:
            self.conf = Conference.get_by_endpoint(endpoint, active=False)
        except ConferenceError:
            raise Http404('Meeting with endpoint "{}" not found'.format(
                endpoint
            ))
        return super(MeetingFormView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs.setdefault('endpoint', self.kwargs.get('endpoint'))
        return super(MeetingFormView, self).get_context_data(**kwargs)

    def get_initial(self):
        self.initial = serialize_meeting(self.conf)
        self.initial.setdefault('edit', True)
        return super(MeetingFormView, self).get_initial()

    def form_valid(self, form):
        custom_fields, data = get_custom_fields(form.cleaned_data)
        if 'admins' in form.changed_data:
            admin_users = get_admin_users(data.get('admins'))
            self.conf.admins = admin_users
        self.conf.name = data.get('name')
        self.conf.info_url = data.get('info_url')
        self.conf.logo_url = data.get('logo_url')
        self.conf.is_meeting = data.get('is_meeting')
        self.conf.active = data.get('active')
        self.conf.public_projects = data.get('public_projects')
        self.conf.poster = data.get('poster')
        self.conf.talk = data.get('talk')
        self.conf.location = data.get('location')
        self.conf.start_date = data.get('start_date')
        self.conf.end_date = data.get('end_date')
        self.conf.field_names.update(custom_fields)
        self.conf.save()
        return super(MeetingFormView, self).form_valid(form)

    @property
    def success_url(self):
        return reverse('meetings:detail',
                       kwargs={'endpoint': self.kwargs.get('endpoint')})


class MeetingCreateFormView(PermissionRequiredMixin, FormView):
    template_name = 'meetings/create.html'
    form_class = MeetingForm
    permission_required = ('osf.view_conference', 'osf.change_conference')
    raise_exception = True

    def get_initial(self):
        self.initial.update(DEFAULT_FIELD_NAMES)
        self.initial.setdefault('edit', False)
        return super(MeetingCreateFormView, self).get_initial()

    def form_valid(self, form):
        custom_fields, data = get_custom_fields(form.cleaned_data)
        endpoint = data.pop('endpoint')
        self.kwargs.setdefault('endpoint', endpoint)
        # Form validation already checks emails for existence
        admin_users = get_admin_users(data.pop('admins'))
        # Note - Mongo was OK with having this in the payload, but Postgres is not
        # This edit variable was unused in the past, but keeping it in case we want to use it in the future.
        data.pop('edit')
        # Form validation already catches if a conference endpoint exists
        new_conf = Conference(
            endpoint=endpoint,
            **data
        )
        new_conf.save()
        new_conf.admins = admin_users
        new_conf.field_names.update(custom_fields)
        new_conf.save()
        return super(MeetingCreateFormView, self).form_valid(form)

    def get_success_url(self):
        return reverse('meetings:detail',
                       kwargs={'endpoint': self.kwargs.get('endpoint')})


def get_custom_fields(data):
    """Return two dicts, one of field_names and the other regular fields."""
    data_copy = deepcopy(data)
    field_names = {}
    for key, value in data.iteritems():
        if key in DEFAULT_FIELD_NAMES:
            field_names[key] = data_copy.pop(key)
    return field_names, data_copy


def get_admin_users(admins):
    """Returns a list of user objects

    If used in conjunction with MeetingForm it will already have checked for
    emails that don't match OSF users.
    """
    return [get_user(email=e) for e in admins]
