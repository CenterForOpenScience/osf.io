from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import render, redirect
from django.views.generic import UpdateView, TemplateView, FormView

from admin.rdm.utils import RdmPermissionMixin

class RdmUserEmailsPermissionMixin(RdmPermissionMixin):
    @property
    def has_auth(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False
        # permitted if superuser or institution administrator
        if self.is_super_admin or self.is_admin:
            return True
        return False

class SearchView(RdmUserEmailsPermissionMixin, UserPassesTestMixin, TemplateView):
    template_name = 'rdm_useremails/search.html'

    def post(self, request, *args, **kwargs):
        return render(request, 'rdm_useremails/result.html')


class ResultView(RdmUserEmailsPermissionMixin, UserPassesTestMixin, TemplateView):
    template_name = 'rdm_useremails/result.html'


class SettingsView(RdmUserEmailsPermissionMixin, UserPassesTestMixin, TemplateView):
    template_name = 'rdm_useremails/settings.html'


