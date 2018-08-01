

import json
from datetime import timedelta

from django.shortcuts import redirect
from django.forms.models import model_to_dict
from django.core.urlresolvers import reverse_lazy
from django.views.generic import ListView, DetailView, View, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib import messages

from admin.banners.forms import BannerForm
from osf.models import ScheduledBanner


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)


def get_blackout_dates(current_banner_id=None):
    blackout_dates = []
    for banner in ScheduledBanner.objects.exclude(id=current_banner_id):
        for dt in daterange(banner.start_date, banner.end_date):
            blackout_dates.append(dt.strftime('%Y-%m-%d'))
    return blackout_dates

class BannerList(PermissionRequiredMixin, ListView):
    paginate_by = 25
    template_name = 'banners/list.html'
    ordering = 'start_date'
    permission_required = 'osf.view_scheduledbanner'
    raise_exception = True
    model = ScheduledBanner

    def get_queryset(self):
        return ScheduledBanner.objects.all().order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('banners', query_set)
        kwargs.setdefault('page', page)
        return super(BannerList, self).get_context_data(**kwargs)


class BannerDisplay(PermissionRequiredMixin, DetailView):
    model = ScheduledBanner
    template_name = 'banners/detail.html'
    permission_required = 'osf.view_scheduledbanner'
    raise_exception = True

    def get_object(self, queryset=None):
        return ScheduledBanner.objects.get(id=self.kwargs.get('banner_id'))

    def get_context_data(self, *args, **kwargs):
        banner = self.get_object()
        banner_dict = model_to_dict(banner)
        kwargs.setdefault('page_number', self.request.GET.get('page', '1'))
        kwargs['banner'] = banner_dict
        fields = banner_dict
        kwargs['change_form'] = BannerForm(initial=fields)
        kwargs['default_photo'] = banner.default_photo.url
        kwargs['mobile_photo'] = banner.mobile_photo.url
        kwargs['blackoutDates'] = json.dumps(get_blackout_dates(banner.id))

        return kwargs


class BannerChangeForm(PermissionRequiredMixin, UpdateView):
    permission_required = 'osf.change_scheduledbanner'
    raise_exception = True
    model = ScheduledBanner
    form_class = BannerForm

    def get_object(self, queryset=None):
        banner_id = self.kwargs.get('banner_id')
        return ScheduledBanner.objects.get(id=banner_id)

    def get_success_url(self, *args, **kwargs):
        return reverse_lazy('banners:detail', kwargs={'banner_id': self.kwargs.get('banner_id')})

    def post(self, request, *args, **kwargs):
        bid = kwargs['banner_id']
        form = BannerForm(request.POST, request.FILES, instance=self.get_object())
        if form.is_valid():
            form.save()
        else:
            for error in form.non_field_errors():
                messages.error(request, error)

        return redirect('banners:detail', banner_id=bid)


class BannerDetail(PermissionRequiredMixin, View):
    permission_required = 'osf.view_scheduledbanner'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        view = BannerDisplay.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = BannerChangeForm.as_view()
        return view(request, *args, **kwargs)

class CreateBanner(PermissionRequiredMixin, CreateView):
    permission_required = 'osf.change_scheduledbanner'
    raise_exception = True
    template_name = 'banners/create.html'
    success_url = reverse_lazy('banners:list')
    model = ScheduledBanner
    form_class = BannerForm

    def get_context_data(self, *args, **kwargs):
        kwargs['blackoutDates'] = json.dumps(get_blackout_dates())
        return super(CreateBanner, self).get_context_data(*args, **kwargs)


class DeleteBanner(PermissionRequiredMixin, DeleteView):
    permission_required = 'osf.delete_scheduledbanner'
    raise_exception = True
    template_name = 'banners/confirm_delete.html'
    success_url = reverse_lazy('banners:list')

    def get_object(self, queryset=None):
        return ScheduledBanner.objects.get(id=self.kwargs['banner_id'])
