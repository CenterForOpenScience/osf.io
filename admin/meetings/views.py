from __future__ import unicode_literals

from django.views.generic import ListView, FormView
from django.core.urlresolvers import reverse
from django.http import Http404

from framework.auth.core import get_user
from website.models import Conference
from website.conferences.exceptions import ConferenceError

from admin.base.utils import OSFAdmin
from admin.meetings.forms import MeetingForm
from admin.meetings.serializers import serialize_meeting


class MeetingListView(OSFAdmin, ListView):
    template_name = 'meetings/list.html'
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


class MeetingFormView(OSFAdmin, FormView):
    template_name = 'meetings/detail.html'
    form_class = MeetingForm

    def dispatch(self, request, *args, **kwargs):
        endpoint = self.kwargs.get('endpoint')
        try:
            self.conf = Conference.get_by_endpoint(endpoint)
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
        self.conf.active = data.get('active')
        self.conf.public_projects = data.get('public_projects')
        self.conf.poster = data.get('poster')
        self.conf.talk = data.get('talk')
        self.conf.field_names.update(custom_fields)
        self.conf.save()
        return super(MeetingFormView, self).form_valid(form)

    @property
    def success_url(self):
        return reverse('meetings:detail',
                       kwargs={'endpoint': self.kwargs.get('endpoint')})


class MeetingCreateFormView(OSFAdmin, FormView):
    template_name = 'meetings/create.html'
    form_class = MeetingForm

    def get_initial(self):
        default_field_names = Conference.DEFAULT_FIELD_NAMES
        self.initial.update({'field_{}'.format(k): default_field_names[k]
                             for k in default_field_names.keys()})
        self.initial.setdefault('edit', False)
        return super(MeetingCreateFormView, self).get_initial()

    def form_valid(self, form):
        custom_fields, data = get_custom_fields(form.cleaned_data)
        endpoint = data.pop('endpoint')
        self.kwargs.setdefault('endpoint', endpoint)
        # Form validation already checks emails for existence
        admin_users = get_admin_users(data.pop('admins'))
        # Form validation already catches if a conference endpoint exists
        new_conf = Conference(
            endpoint=endpoint,
            admins=admin_users,
            **data
        )
        new_conf.field_names.update(custom_fields)
        new_conf.save()
        return super(MeetingCreateFormView, self).form_valid(form)

    def get_success_url(self):
        return reverse('meetings:detail',
                       kwargs={'endpoint': self.kwargs.get('endpoint')})


def get_custom_fields(data):
    """Return two dicts, one with 'field' stripped
     and the other that didn't have 'field' in the first place.
    """
    fields = {'_'.join(k.split('_')[1:]): data[k]
              for k in data.keys() if 'field' in k}
    non_fields = {k: data[k] for k in data.keys() if 'field' not in k}
    return fields, non_fields


def get_admin_users(admins):
    """Returns a list of user objects

    If used in conjunction with MeetingForm it will already have checked for
    emails that don't match OSF users.
    """
    return [get_user(email=e) for e in admins]
