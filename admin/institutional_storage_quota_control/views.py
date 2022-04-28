from django.db import connection

from admin.institutions.views import QuotaUserList
from osf.models import Institution, OSFUser, UserQuota
from admin.base import settings
from addons.osfstorage.models import Region
from django.views.generic import ListView, View
from django.shortcuts import redirect
from admin.rdm.utils import RdmPermissionMixin
from django.core.urlresolvers import reverse
from django.db.models import Q


class InstitutionStorageList(RdmPermissionMixin, ListView):
    paginate_by = 25
    template_name = 'institutional_storage_quota_control/' \
                    'list_institution_storage.html'
    ordering = 'name'
    raise_exception = True
    model = Institution

    def get(self, request, *args, **kwargs):
        count = 0
        institution_id = 0
        query_set = self.get_queryset()
        self.object_list = query_set

        for item in query_set:
            if item.institution_id:
                institution_id = item.institution_id
                count += 1
            else:
                self.object_list = self.object_list.exclude(id=item.id)

        ctx = self.get_context_data()

        if self.is_super_admin:
            return self.render_to_response(ctx)
        elif self.is_admin:
            if count == 1:
                return redirect(reverse(
                    'institutional_storage_quota_control:'
                    'institution_user_list',
                    kwargs={'institution_id': institution_id}
                ))
            return self.render_to_response(ctx)

    def get_queryset(self):
        if self.is_super_admin:
            query = 'select {} ' \
                    'from osf_institution ' \
                    'where addons_osfstorage_region._id = osf_institution._id'
            return Region.objects.filter(
                ~Q(waterbutler_settings__storage__provider='filesystem'))\
                .extra(select={'institution_id': query.format('id'),
                               'institution_name': query.format('name'),
                               'institution_logo_name': query.format(
                                   'logo_name'),
                               }).order_by('institution_name', self.ordering)

        elif self.is_admin:
            user_id = self.request.user.id
            query = 'select {} ' \
                    'from osf_institution ' \
                    'where addons_osfstorage_region._id = _id ' \
                    'and id in (' \
                    '    select institution_id ' \
                    '    from osf_osfuser_affiliated_institutions ' \
                    '    where osfuser_id = {}' \
                    ')'
            return Region.objects.filter(
                ~Q(waterbutler_settings__storage__provider='filesystem'))\
                .extra(select={'institution_id': query.format('id', user_id),
                               'institution_name': query.format(
                                   'name',
                                   user_id),
                               'institution_logo_name': query.format(
                                   'logo_name',
                                   user_id),
                               })

    def get_context_data(self, **kwargs):
        query_set = kwargs.pop('object_list', self.object_list)
        page_size = self.get_paginate_by(query_set)
        paginator, page, query_set, is_paginated = self.paginate_queryset(
            query_set,
            page_size
        )
        kwargs.setdefault('institutions', query_set)
        kwargs.setdefault('page', page)
        kwargs.setdefault('logohost', settings.OSF_URL)
        return super(InstitutionStorageList, self).get_context_data(**kwargs)


class UserListByInstitutionStorageID(RdmPermissionMixin, QuotaUserList):
    template_name = 'institutional_storage_quota_control/list_institute.html'
    raise_exception = True
    paginate_by = 25

    def get_userlist(self):
        user_list = []
        for user in OSFUser.objects.filter(
                affiliated_institutions=self.kwargs['institution_id']):
            user_list.append(self.get_user_quota_info(
                user, UserQuota.CUSTOM_STORAGE)
            )
        return user_list

    def get_institution(self):
        query = 'select name '\
                'from addons_osfstorage_region '\
                'where addons_osfstorage_region._id = osf_institution._id'
        institution = Institution.objects.filter(
            id=self.kwargs['institution_id']
        ).extra(
            select={
                'storage_name': query,
            }
        )
        return institution.first()


class UpdateQuotaUserListByInstitutionStorageID(RdmPermissionMixin, View):
    raise_exception = True

    def post(self, request, *args, **kwargs):
        institution_id = self.kwargs['institution_id']
        min_value, max_value = connection.ops.integer_field_range('IntegerField')
        max_quota = min(int(self.request.POST.get('maxQuota')), max_value)
        for user in OSFUser.objects.filter(
                affiliated_institutions=institution_id):
            UserQuota.objects.update_or_create(
                user=user,
                storage_type=UserQuota.CUSTOM_STORAGE,
                defaults={'max_quota': max_quota}
            )
        return redirect(
            'institutional_storage_quota_control:institution_user_list',
            institution_id=institution_id
        )
