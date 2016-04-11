from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView, ProcessFormView
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse
from django.utils import timezone
from forms import ConferenceForm, ConferenceFieldNamesForm
from .serializers import serialize_conference

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from framework.auth.core import User

from website import settings
from website.conferences.model import Conference
from website.app import init_app



# Create your views here.
def create_conference(request):
    if request.user.is_staff:
        conf_form = ConferenceForm(request.POST or None)
        conf_field_names_form = ConferenceFieldNamesForm(request.POST or None)
        if request.POST and conf_form.is_valid():
            conf = Conference(
                name=request.POST['name'],
                endpoint=request.POST['endpoint'],
                info_url=request.POST['info_url'],
                logo_url=request.POST['logo_url'],
                active=request.POST.get('active', True),
                public_projects=request.POST.get('public_projects', True),
                poster=request.POST.get('poster', True),
                talk=request.POST.get('talk', True),
            )
            # if (conf_field_names_form.has_changed):
            # conf.field_names.update(custom_fields)
            try:
                conf.save()
            except ModularOdmException:
                print('failed')
                # conf = Conference.find_one(Q('endpoint', 'eq', meeting))
                # for key, value in attrs.items():
                #     if isinstance(value, dict):
                #         current = getattr(conf, key)
                #         current.update(value)
                #         setattr(conf, key, current)
                #     else:
                #         setattr(conf, key, value)
                # conf.admins = admin_objs
                # changed_fields = conf.save()
                # if changed_fields:
                #     print('Updated {}: {}'.format(meeting, changed_fields))
            else:
                print('success')
                messages.success(request, 'success')
            return redirect('conferences:create_conference')


        else:
            context = {'conf_form': conf_form, 'conf_field_names_form': conf_field_names_form}
            return render(request, 'conferences/create_conference.html', context)
    else:
        messages.error(request, 'You do not have permission to access that page.')
        return redirect('auth:login')

class ConferenceList(ListView):
    template_name = 'conferences/conference_list.html'
    paginate_by = 10
    paginate_orphans = 1
    ordering = 'date_created'
    context_object_name = 'conference'

    def get_queryset(self):
        query = (
            Q('active', 'eq', True) # What is the query for .all()?
        )
        return Conference.find(query).sort(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        return {
            'conferences': map(serialize_conference, query_set),
            'page': page,
        }
