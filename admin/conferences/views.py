from django.shortcuts import render, redirect
from django.contrib import messages
from forms import ConferenceForm, ConferenceFieldNamesForm
from .models import Conference
from website.conferences.model import Conference as OSF_Conference
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView, ProcessFormView
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse
from django.utils import timezone

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from framework.auth.core import User

from website import settings
from website.app import init_app



# Create your views here.
def create_conference(request):
    if request.user.is_staff:
        conf_form = ConferenceForm(request.POST)
        conf_field_names_form = ConferenceFieldNamesForm(request.POST)
        if request.method == 'POST':
            if all((conf_form.is_valid(), conf_field_names_form.is_valid())):
                new_conference = conf_form.save()
                new_conference_field_names = conf_field_names_form.save()
                new_conference_field_names.save()
                new_conference.field_names = new_conference_field_names
                new_conference.save()
                print('seems to have worked')
                # Save with commit=False to do stuff here if need be

                return redirect('conferences:create_conference')
            else:
                print(form.errors)
                messages.error(request, 'Test..')
                return redirect('conferences:create_conference')
        else:
            context = {'conf_form': conf_form, 'conf_field_names_form': conf_field_names_form}
            return render(request, 'conferences/create_conference.html', context)
    else:
        messages.error(request, 'You do not have permission to access that page.')
        return redirect('auth:login')

# check if at least one exists, otherwise do something else
class ConfDetailView(DetailView):
    model = Conference
    template_name = 'create_conference.html'

    def get_context_data(self, **kwargs):
        context = super(ConfDetailView, self).get_context_data(**kwargs)
        context['form'] = ConferenceForm
        return context

class ConfFormView(FormView, ProcessFormView):
    form_class = ConferenceForm
   # success_url = "/conferences/"

class ConfListView(ListView):
    model = Conference

    def get_context_data(self, **kwargs):
        context = super(ConfListView, self).get_context_data(**kwargs)
        context['now'] = timezone.now()
        return context



def add_conference_to_OSF(self):
    objects = Conference.objects.all()
    for obj in objects:
        endpoint = obj.endpoint
        admin_email = obj.admins # should be one or more
        admin_objs = []
       #
        try:
            user = User.find_one(Q('username', 'iexact', admin_email))
            admin_objs.append(user)
        except ModularOdmException:
           # raise RuntimeError('Username {0!r} is not registered.'.format(admin_email))
            pass

        #custom_fields = obj.field_names

        conf = OSF_Conference(
            endpoint=obj.endpoint, name=obj.name, info_url=obj.info_url, logo_url=obj.logo_url,
            active=obj.active, admins=admin_objs, public_projects= obj.public_projects,
            poster=obj.poster, talk=obj.talk, num_submissions=obj.num_submissions  # Is there a way to get a dict of each obj's fields/values
        )                                                                           # and pass with **?
        #conf.field_names.update(custom_fields)
        try:
            conf.save()
        except ModularOdmException as error:
            # conf = OSF_Conference.find_one(Q('endpoint', 'eq', endpoint))
            # for key, value in objects.items():
            #     if isinstance(value, dict):
            #         current = getattr(conf, key)
            #         current.update(value)
            #         setattr(conf, key, current)
            #     else:
            #         setattr(conf, key, value)
            print('ModularOdmException happened here')
            print(obj.endpoint)
            print '%s (%s)' % (error.message, type(error))
            # conf.admins = admin_objs
            # changed_fields = conf.save() # getting error 'Value must be unique'
            # if changed_fields:
            #     print('Updated {}: {}'.format(endpoint, changed_fields))
            #     return redirect('auth:login')
            # else:
            return redirect('auth:login')

        print('Added new Conference: {}'.format(endpoint))
        return redirect('auth:login')


