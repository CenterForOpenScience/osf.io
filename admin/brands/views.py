from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import (
    View,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
)
from django.core.urlresolvers import reverse_lazy
from django.forms.models import model_to_dict
from django.contrib import messages

from osf.models import Brand
from osf.utils.sanitize import is_a11y

from admin.brands.forms import BrandForm


class BrandList(PermissionRequiredMixin, ListView):
    paginate_by = 20
    template_name = 'brands/list.html'
    ordering = 'id'
    permission_required = 'osf.view_brand'
    raise_exception = True
    model = Brand

    def get_queryset(self):
        return Brand.objects.all().order_by(self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set, page_size)
        kwargs.setdefault('brands', query_set)
        kwargs.setdefault('page', page)
        return super(BrandList, self).get_context_data(**kwargs)


class BrandDisplay(PermissionRequiredMixin, DetailView):
    model = Brand
    template_name = 'brands/detail.html'
    permission_required = 'osf.view_brand'
    raise_exception = True

    def get_object(self, queryset=None):
        return Brand.objects.get(id=self.kwargs.get('brand_id'))

    def get_context_data(self, *args, **kwargs):
        brand = self.get_object()
        brand_dict = model_to_dict(brand)
        kwargs['brand'] = brand_dict
        fields = brand_dict
        kwargs['change_form'] = BrandForm(initial=fields)

        return kwargs

class BrandChangeForm(PermissionRequiredMixin, UpdateView):
    permission_required = 'osf.modify_brand'
    raise_exception = True
    model = Brand
    form_class = BrandForm

    def get_object(self, queryset=None):
        brand_id = self.kwargs.get('brand_id')
        return Brand.objects.get(id=brand_id)

    def get_success_url(self, *args, **kwargs):
        brand_id = self.kwargs.get('brand_id')
        return reverse_lazy('brands:detail', kwargs={'brand_id': brand_id})

class BrandDetail(PermissionRequiredMixin, View):
    permission_required = 'osf.view_brand'
    raise_exception = True

    def get(self, request, *args, **kwargs):
        view = BrandDisplay.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = BrandChangeForm.as_view()
        primary_color = request.POST.get('primary_color')
        secondary_color = request.POST.get('secondary_color')

        if not is_a11y(primary_color):
            messages.warning(request, """The selected primary color is not a11y compliant.
                For more information, visit https://color.a11y.com/""")
        if not is_a11y(secondary_color):
            messages.warning(request, """The selected secondary color is not a11y compliant.
                For more information, visit https://color.a11y.com/""")
        return view(request, *args, **kwargs)


class BrandCreate(PermissionRequiredMixin, CreateView):
    permission_required = 'osf.modify_brand'
    raise_exception = True
    template_name = 'brands/create.html'
    model = Brand
    form_class = BrandForm

    def get_success_url(self, *args, **kwargs):
        brand = Brand.objects.filter(name=self.request.POST['name']).first()
        return reverse_lazy('brands:detail', kwargs={'brand_id': brand.id})

    def get_context_data(self, *args, **kwargs):
        kwargs['change_form'] = BrandForm()
        return kwargs

    def post(self, request, *args, **kwargs):
        primary_color = request.POST.get('primary_color')
        secondary_color = request.POST.get('secondary_color')

        if not is_a11y(primary_color):
            messages.warning(request, """The selected primary color is not a11y compliant.
                For more information, visit https://color.a11y.com/""")
        if not is_a11y(secondary_color):
            messages.warning(request, """The selected secondary color is not a11y compliant.
                For more information, visit https://color.a11y.com/""")
        return super(BrandCreate, self).post(request, *args, **kwargs)
