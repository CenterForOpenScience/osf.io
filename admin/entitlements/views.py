from __future__ import unicode_literals

from django.views.generic import ListView

from admin.base import settings
from admin.entitlements.forms import InstitutionEntitlementForm
from osf.models import Institution, InstitutionEntitlement


class InstitutionEntitlementList(ListView):
    paginate_by = 25
    template_name = 'entitlements/list.html'
    permission_required = 'osf.admin_institution_entitlement'
    raise_exception = True
    model = InstitutionEntitlement

    def get_queryset(self):
        institutions = Institution.objects.all().order_by(self.ordering)
        return InstitutionEntitlement.objects.get(institution_id=institutions.first().id).login_availability

    def get_context_data(self, **kwargs):
        institutions = Institution.objects.all().order_by(self.ordering)

        selected_id = kwargs.pop('selected_id', institutions.first().id)
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('institutions', institutions)
        kwargs.setdefault('selected_id', selected_id)
        kwargs.setdefault('entitlements', query_set)
        kwargs.setdefault('page', page)
        return super(InstitutionEntitlementList, self).get_context_data(**kwargs)
