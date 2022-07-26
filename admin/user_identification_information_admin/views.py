import csv
from django.db.models import Q
from django.http import Http404
from django.http import HttpResponse
from django.views.generic import ListView
from operator import itemgetter

from admin.base.views import GuidView
from admin.rdm.utils import RdmPermissionMixin
from api.base import settings as api_settings
from osf.models import OSFUser, UserQuota, Email
from osf.models.files import BaseFileNode, FileVersion, BaseFileVersionsThrough
from website.util import quota


def custom_size_abbreviation(size, abbr, *kwargs):
    if abbr == 'B':
        return (size / api_settings.BASE_FOR_METRIC_PREFIX, 'KB')
    return size, abbr


def check_extended_storage(user):
    fileVersion = FileVersion.objects.filter(creator=user).values_list('id', flat=True)
    base = BaseFileVersionsThrough.objects.filter(fileversion_id__in=fileVersion).values_list('basefilenode_id',
                                                                                              flat=True)
    check_provider = set(BaseFileNode.objects.filter(id__in=base).values_list('provider', flat=True))

    if len(check_provider) > 1:
        return True
    elif len(check_provider) == 1:
        for provider in check_provider:
            if provider in 'osfstorage':
                return False
            else:
                return True
    else:
        return False


class UserIdentificationInformation(ListView):

    def get_user_quota_info(self, user, storage_type):
        _, used_quota = quota.get_quota_info(user, storage_type)
        used_quota_abbr = custom_size_abbreviation(*quota.abbreviate_size(used_quota))

        return {
            'id': user.guids.first()._id,
            'fullname': user.fullname,
            'eppn': user.eppn or '',
            'affiliation': user.affiliated_institutions.first(),
            'email': user.emails.values_list('address', flat=True)[0] or '',
            'last_login': user.last_login or '',
            'usage': used_quota,
            'usage_value': used_quota_abbr[0],
            'usage_abbr': used_quota_abbr[1],
            'extended_storage': check_extended_storage(user),
        }

    def get_queryset(self):
        user_list = self.get_userlist()
        order_by = self.get_order_by()
        reverse = self.get_direction() != 'asc'
        user_list.sort(key=itemgetter(order_by), reverse=reverse)
        return user_list

    def get_order_by(self):
        order_by = self.request.GET.get('order_by', 'usage')
        if order_by not in ['fullname', 'eppn', 'last_login', 'usage', 'affiliation', 'email', 'extended_storage']:
            return 'usage'
        return order_by

    def get_direction(self):
        direction = self.request.GET.get('status', 'desc')
        if direction not in ['asc', 'desc']:
            return 'desc'
        return direction

    def get_context_data(self, **kwargs):
        if self.request.user.is_superuser:
            raise Http404('Page not found')
        self.query_set = self.get_queryset()
        self.page_size = self.get_paginate_by(self.query_set)
        self.paginator, self.page, self.query_set, self.is_paginated = \
            self.paginate_queryset(self.query_set, self.page_size)
        kwargs['requested_user'] = self.request.user
        kwargs[
            'institution_name'] = self.request.user.affiliated_institutions.first().name \
            if self.request.user.is_superuser is False else None
        kwargs['users'] = self.query_set
        kwargs['page'] = self.page
        kwargs['order_by'] = self.get_order_by()
        kwargs['direction'] = self.get_direction()
        return super(UserIdentificationInformation, self).get_context_data(**kwargs)


class UserIdentificationList(RdmPermissionMixin, UserIdentificationInformation):
    template_name = 'user_identification_information/list_user_identification.html'
    permission_required = ''
    raise_exception = True
    paginate_by = 20

    def get_userlist(self):

        guid = self.request.GET.get('guid')
        name = self.request.GET.get('fullname')
        email = self.request.GET.get('username')
        queryset = []
        if self.request.user.is_superuser is False:
            institution = self.request.user.affiliated_institutions.first()
            if institution is not None:  # and Region.objects.filter(_id=institution._id).exists():
                queryset = OSFUser.objects.filter(affiliated_institutions=institution.id).order_by('id')
        else:
            queryset = OSFUser.objects.all().order_by('id')
        if not email and not guid and not name:
            return [self.get_user_quota_info(user, UserQuota.NII_STORAGE) for user in queryset]
        query_email = query_guid = query_name = None
        if email:
            existing_user_ids = list(Email.objects.filter(Q(address__exact=email)).values_list('user_id', flat=True))
            query_email = queryset.filter(Q(pk__in=existing_user_ids) | Q(username__exact=email))
        if guid:
            query_guid = queryset.filter(guids___id=guid)
        if name:
            query_name = queryset.filter(Q(fullname__icontains=name) |
                                         Q(family_name_ja__icontains=name) |
                                         Q(given_name_ja__icontains=name) |
                                         Q(middle_names_ja__icontains=name) |
                                         Q(given_name__icontains=name) |
                                         Q(middle_names__icontains=name) |
                                         Q(family_name__icontains=name))

        if query_email is not None and query_email.exists():
            return [self.get_user_quota_info(user, UserQuota.NII_STORAGE) for user in query_email]
        elif query_guid is not None and query_guid.exists():
            return [self.get_user_quota_info(user, UserQuota.NII_STORAGE) for user in query_guid]
        elif query_name is not None and query_name.exists():
            return [self.get_user_quota_info(user, UserQuota.NII_STORAGE) for user in query_name]
        else:
            return []


class UserIdentificationDetails(RdmPermissionMixin, GuidView):
    template_name = 'user_identification_information/user_identification_details.html'
    context_object_name = 'user_details'
    permission_required = ''
    raise_exception = True

    def get_object(self):
        if self.request.user.is_superuser:
            raise Http404('Page not found')
        user_details = OSFUser.load(self.kwargs.get('guid'))
        max_quota, used_quota = quota.get_quota_info(user_details, UserQuota.NII_STORAGE)
        max_quota_bytes = max_quota * api_settings.SIZE_UNIT_GB
        remaining_quota = max_quota_bytes - used_quota

        used_quota_abbr = custom_size_abbreviation(*quota.abbreviate_size(used_quota))
        remaining_abbr = custom_size_abbreviation(*quota.abbreviate_size(remaining_quota))
        max_quota, _ = quota.get_quota_info(user_details, UserQuota.NII_STORAGE)

        return {
            'username': user_details.username,
            'name': user_details.fullname,
            'id': user_details._id,
            'emails': user_details.emails.values_list('address', flat=True),
            'last_login': user_details.date_last_login,
            'confirmed': user_details.date_confirmed,
            'registered': user_details.date_registered,
            'disabled': user_details.date_disabled if user_details.is_disabled else False,
            'two_factor': user_details.has_addon('twofactor'),
            'osf_link': user_details.absolute_url,
            'system_tags': user_details.system_tags or '',
            'quota': max_quota,
            'affiliation': user_details.affiliated_institutions.first() or '',
            'usage': used_quota,
            'usage_value': used_quota_abbr[0],
            'usage_abbr': used_quota_abbr[1],
            'remaining': remaining_quota,
            'remaining_value': remaining_abbr[0],
            'remaining_abbr': remaining_abbr[1],
            'extended_storage': check_extended_storage(user_details),
        }


class ExportFileCSV(RdmPermissionMixin, UserIdentificationInformation):

    def get(self, request, **kwargs):

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment;filename=export.csv'
        writer = csv.writer(response)
        writer.writerow(
            ['GUID', 'EPPN', 'Fullname', 'Email', 'Affiliation', 'Last login', 'Usage (Byte)', 'Extended storage'])
        queryset = []

        if self.request.user.is_superuser is False:
            institution = self.request.user.affiliated_institutions.first()
            if institution is not None:  # and Region.objects.filter(_id=institution._id).exists():
                queryset = OSFUser.objects.filter(affiliated_institutions=institution.id).order_by('id')
        else:
            queryset = OSFUser.objects.all().order_by('id')
        for user in queryset:
            max_quota, used_quota = quota.get_quota_info(user, UserQuota.NII_STORAGE)

            writer.writerow([user.guids.first()._id,
                             user.eppn,
                             user.fullname,
                             user.emails.values_list('address', flat=True)[0],
                             user.affiliated_institutions.first().name if user.affiliated_institutions.first() else '',
                             user.last_login,
                             used_quota,
                             check_extended_storage(user)])
        return response
