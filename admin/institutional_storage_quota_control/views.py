from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import connection
from django.db.models import Subquery, OuterRef
from django.http import Http404

from admin.institutions.views import QuotaUserList
from osf.models import Institution, OSFUser, UserQuota
from admin.base import settings
from addons.osfstorage.models import Region
from django.views.generic import ListView, View
from django.shortcuts import redirect
from admin.rdm.utils import RdmPermissionMixin
from django.core.urlresolvers import reverse


class InstitutionStorageList(RdmPermissionMixin, UserPassesTestMixin, ListView):
    """List of institutions that are not using NII Storage screen.
    If currently logged in as an institution administrator and has only one affiliated institution, redirect to user list screen.
    """
    paginate_by = 25
    template_name = 'institutional_storage_quota_control/' \
                    'list_institution_storage.html'
    ordering = 'name'
    raise_exception = True
    model = Institution

    def test_func(self):
        """determine whether the user has institution permissions"""
        # login check
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page
            self.raise_exception = False
            return False
        # allowed if superuser
        if self.is_super_admin:
            return True
        elif self.is_admin:
            # allowed if admin
            # ignore check self.is_affiliated_institution(institution_id)
            return True
        return False

    def get(self, request, *args, **kwargs):
        """ Handle GET request """
        query_set = self.get_queryset()
        if self.is_admin and len(query_set) == 1:
            # If user is administrator and has only one affiliated institution then redirect to user list page
            return redirect(reverse(
                'institutional_storage_quota_control:'
                'institution_user_list',
                kwargs={'institution_id': query_set.first().id}
            ))
        return super(InstitutionStorageList, self).get(request, *args, **kwargs)

    def get_queryset(self):
        """ Get institutions that are not using NII Storage """
        if self.is_super_admin:
            return Institution.objects.annotate(
                storage_name=Subquery(Region.objects.filter(_id=OuterRef('_id')).values('name'))
            ).filter(
                is_deleted=False,
                _id__in=Region.objects.filter(waterbutler_settings__storage__type=Region.INSTITUTIONS).values('_id')
            ).order_by(self.ordering)
        elif self.is_admin:
            return Institution.objects.annotate(
                storage_name=Subquery(Region.objects.filter(_id=OuterRef('_id')).values('name'))
            ).filter(
                is_deleted=False,
                _id__in=Region.objects.filter(waterbutler_settings__storage__type=Region.INSTITUTIONS).values('_id'),
                id__in=self.request.user.affiliated_institutions.values('id')
            ).order_by(self.ordering)

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


class UserListByInstitutionStorageID(RdmPermissionMixin, UserPassesTestMixin, QuotaUserList):
    """ User list quota info screen for an institution that is not using NII Storage. """
    template_name = 'institutional_storage_quota_control/list_institute.html'
    raise_exception = True
    paginate_by = 25
    institution_id = None

    def test_func(self):
        """check user permissions"""
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page
            self.raise_exception = False
            return False
        self.institution_id = int(self.kwargs.get('institution_id'))
        if not Institution.objects.filter(id=self.institution_id, is_deleted=False).exists():
            # If institution_id does not exist, redirect to HTTP 404 page
            raise Http404
        return self.has_auth(self.institution_id)

    def get_userlist(self):
        """ Get user list by institution_id """
        user_list = []
        for user in OSFUser.objects.filter(
                affiliated_institutions=self.institution_id):
            user_list.append(self.get_user_quota_info(
                user, UserQuota.CUSTOM_STORAGE)
            )
        return user_list

    def get_institution(self):
        """ Get institution that is not using NII Storage """
        # Get institution that is not using NII Storage
        region__ids = Region.objects.filter(waterbutler_settings__storage__type=Region.INSTITUTIONS).values('_id')
        institution = Institution.objects.filter(is_deleted=False, _id__in=region__ids, id=self.institution_id).first()
        if not institution:
            # If institution is not found, redirect to HTTP 404 page
            raise Http404
        return institution


class UpdateQuotaUserListByInstitutionStorageID(RdmPermissionMixin, UserPassesTestMixin, View):
    """ Change max quota for an institution's users if that institution is not using NII Storage. """
    raise_exception = True
    institution_id = None

    def test_func(self):
        """check user permissions"""
        if not self.is_authenticated:
            # If user is not authenticated then redirect to login page
            self.raise_exception = False
            return False
        self.institution_id = int(self.kwargs.get('institution_id'))
        if not Institution.objects.filter(id=self.institution_id).exists():
            # If institution_id does not exist, redirect to HTTP 404 page
            raise Http404
        return self.has_auth(self.institution_id)

    def post(self, request, *args, **kwargs):
        """ Handle POST request """
        # Validate maxQuota parameter
        try:
            max_quota = self.request.POST.get('maxQuota')
            # Try converting maxQuota param to integer
            max_quota = int(max_quota)
        except (ValueError, TypeError):
            # Cannot convert maxQuota param to integer, redirect to the current page
            return redirect(
                'institutional_storage_quota_control:institution_user_list',
                institution_id=self.institution_id
            )

        # Get institution that is not using NII Storage
        region__ids = Region.objects.filter(waterbutler_settings__storage__type=Region.INSTITUTIONS).values('_id')
        institution = Institution.objects.filter(is_deleted=False, id=self.institution_id, _id__in=region__ids).first()
        if not institution:
            # If institution is not found, redirect to HTTP 404 page
            raise Http404
        min_value, max_value = connection.ops.integer_field_range('PositiveIntegerField')
        if min_value <= max_quota <= max_value:
            # If max quota value is between 0 and 2147483647, update or create used quota for each user in the institution
            for user in OSFUser.objects.filter(
                    affiliated_institutions=self.institution_id):
                UserQuota.objects.update_or_create(
                    user=user,
                    storage_type=UserQuota.CUSTOM_STORAGE,
                    defaults={'max_quota': max_quota}
                )
        return redirect(
            'institutional_storage_quota_control:institution_user_list',
            institution_id=self.institution_id
        )
