from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, redirect
from django.views.generic import UpdateView, TemplateView, FormView
from django.contrib.auth.mixins import PermissionRequiredMixin
from admin.rdm_useremails.forms import SearchForm

from django.db.models import Q
from osf.models.user import OSFUser

from django.urls import reverse

from django.views.defaults import page_not_found

class SearchView(PermissionRequiredMixin, FormView):
    template_name = 'users/search.html'
    object_type = 'osfuser'
    permission_required = 'osf.view_osfuser'
    raise_exception = True
    form_class = SearchForm

    def __init__(self, *args, **kwargs):
        self.redirect_url = None
        super(SearchView, self).__init__(*args, **kwargs)

    def form_valid(self, form):
        guid = form.cleaned_data['guid']
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']

        if guid or email:
            if email:
                try:
                    user = OSFUser.objects.filter(Q(username=email) | Q(emails__address=email)).distinct('id').get()
                    guid = user.guids.first()._id
                except OSFUser.DoesNotExist:
                    return page_not_found(self.request, AttributeError('User with email address {} not found.'.format(email)))
                except OSFUser.MultipleObjectsReturned:
                    self.redirect_url = reverse('useremails:result', kwargs={'guid': guid})

            self.redirect_url = reverse('users:user', kwargs={'guid': guid})
        elif name:
            self.redirect_url = reverse('users:search_list', kwargs={'name': name})

        return super(UserFormView, self).form_valid(form)

    @property
    def success_url(self):
        return self.redirect_url

class ResultView(PermissionRequiredMixin, TemplateView):
    template_name = 'rdm_useremails/result.html'


class SettingsView(PermissionRequiredMixin, TemplateView):
    template_name = 'rdm_useremails/settings.html'


