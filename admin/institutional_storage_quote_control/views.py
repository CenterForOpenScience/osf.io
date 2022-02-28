from admin.institutions.views import QuotaUserList
from osf.models import Institution, OSFUser, UserQuota
from admin.base import settings
from addons.osfstorage.models import Region
from django.views.generic import ListView, View, DetailView
from django.shortcuts import redirect
from admin.rdm.utils import RdmPermissionMixin
from django.core.urlresolvers import reverse


class InstitutionStorageList(RdmPermissionMixin, ListView):
    paginate_by = 3
    template_name = 'institutional_storage_quote_control/list_institution_storage.html'
    ordering = 'name'
    raise_exception = True
    model = Institution

    def get(self, request, *args, **kwargs):
        if self.is_super_admin:
            self.object_list = self.get_queryset()
            ctx = self.get_context_data()
            return self.render_to_response(ctx)
        elif self.is_admin:
            self.object_list = self.get_queryset()
            ctx = self.get_context_data()
            count = 0
            institution_id = 0
            for item in self.object_list:
                if item.institution_id:
                    institution_id = item.institution_id
                    count += 1
                else:
                    self.object_list.exclude(id=item.id)
                if count > 1:
                    return self.render_to_response(ctx)
            if count == 1:
                return redirect(reverse('institutional_storage_quote_control:institution_user_list',
                                        kwargs={'institution_id': institution_id}))
            return self.render_to_response(ctx)

    def get_queryset(self):
        user_id = self.request.user.id

        if self.is_super_admin:
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
        elif self.is_admin:
            return Region.objects.filter(waterbutler_settings__storage__provider='filesystem').extra(select={
                'institution_id': 'select id '
                                  'from osf_institution '
                                  'where addons_osfstorage_region._id = osf_institution._id '
                                  'and id in ('
                                  '    select institution_id '
                                  '    from osf_osfuser_affiliated_institutions '
                                  '    where osfuser_id = {}'
                                  ')'.format(user_id),

                'institution_name': 'select name '
                                    'from osf_institution '
                                    'where addons_osfstorage_region._id = osf_institution._id '
                                    'and id in ('
                                    '    select institution_id '
                                    '    from osf_osfuser_affiliated_institutions '
                                    '    where osfuser_id = {}'
                                    ')'.format(user_id),

                'institution_logo_name': 'select logo_name '
                                         'from osf_institution '
                                         'where addons_osfstorage_region._id = osf_institution._id '
                                         'and id in ('
                                         '    select institution_id '
                                         '    from osf_osfuser_affiliated_institutions '
                                         '    where osfuser_id = {}'
                                         ')'.format(user_id),
            })

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(query_set, page_size)
        kwargs.setdefault('institutions', query_set)
        kwargs.setdefault('page', page)
        kwargs.setdefault('logohost', settings.OSF_URL)
        return super(InstitutionStorageList, self).get_context_data(**kwargs)


class UserListByInstitutionStorageID(RdmPermissionMixin, QuotaUserList):
    template_name = 'institutional_storage_quote_control/list_institute.html'
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
        return institution.first()


class UpdateQuotaUserListByInstitutionStorageID(RdmPermissionMixin, View):
    raise_exception = True

    def post(self, request, *args, **kwargs):
        institution_id = self.kwargs['institution_id']
        max_quota = self.request.POST.get('maxQuota')
        for user in OSFUser.objects.filter(affiliated_institutions=institution_id):
           UserQuota.objects.update_or_create(user=user, storage_type=UserQuota.CUSTOM_STORAGE, defaults={'max_quota': max_quota})
        return redirect('institutional_storage_quote_control:institution_user_list', institution_id=institution_id)
