from django.contrib.auth.mixins import PermissionRequiredMixin, UserPassesTestMixin
from admin.institutions.views import QuotaUserList
from osf.models import Institution, OSFUser, UserQuota
from admin.base import settings
from addons.osfstorage.models import Region
from django.views.generic import ListView, View, DetailView
from django.shortcuts import redirect


class InstitutionStorageList(PermissionRequiredMixin, ListView):
    paginate_by = 5
    template_name = 'institutional_storage_quote_control/list_institution_storage.html'
    ordering = 'name'
    permission_required = 'osf.view_institution'
    raise_exception = True
    model = Institution

    def get_queryset(self):

        return Region.objects.filter(waterbutler_settings__storage__provider='filesystem').extra(select={
            'institution_id': 'select id '
                              'from osf_institution '
                              'where addons_osfstorage_region._id = osf_institution._id',
            'institution_name': 'select name '
                                'from osf_institution '
                                'where addons_osfstorage_region._id = osf_institution._id',
            'institution_logo_name': 'select logo_name '
                                     'from osf_institution '
                                     'where addons_osfstorage_region._id = osf_institution._id',
        }).order_by('institution_name', self.ordering)

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('institutions', query_set)
        kwargs.setdefault('page', page)
        kwargs.setdefault('logohost', settings.OSF_URL)
        return super(InstitutionStorageList, self).get_context_data(**kwargs)


class UserListByInstitutionStorageID(PermissionRequiredMixin, QuotaUserList):
    template_name = 'institutional_storage_quote_control/list_institute.html'
    permission_required = 'osf.view_institution'
    raise_exception = True
    paginate_by = 10

    def get_userlist(self):
        user_list = []
        for user in OSFUser.objects.filter(affiliated_institutions=self.kwargs['institution_id']):
            user_list.append(self.get_user_quota_info(user, UserQuota.CUSTOM_STORAGE))
        return user_list

    def get_institution(self):
        institution = Institution.objects.filter(id=self.kwargs['institution_id']).extra(
            select={
                'storage_name': 'select name '
                                'from addons_osfstorage_region '
                                'where addons_osfstorage_region._id = osf_institution._id',
            }
        )
        return institution[0]


class UpdateQuotaUserListByInstitutionStorageID(PermissionRequiredMixin, View):
    permission_required = 'osf.view_institution'
    raise_exception = True

    def post(self, request, *args, **kwargs):
        institution_id = self.kwargs['institution_id']
        max_quota = self.request.POST.get('maxQuota')
        for user in OSFUser.objects.filter(affiliated_institutions=institution_id):
           UserQuota.objects.update_or_create(user=user, storage_type=UserQuota.CUSTOM_STORAGE, defaults={'max_quota': max_quota})
        return redirect('institutional_storage_quote_control:institution_user_list', institution_id=institution_id)
