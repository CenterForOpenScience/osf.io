from django.http import JsonResponse
from django.db import transaction

from addons.osfstorage.models import Region
from api.base import settings as api_settings
from osf.models import OSFUser, UserQuota
from osf.utils.requests import check_select_for_update
from website.util.quota import used_quota


def calculate_quota(user):
    storage_type_list = [UserQuota.NII_STORAGE]

    institution = user.affiliated_institutions.first()
    if institution is not None and Region.objects.filter(_id=institution._id).exists():
        storage_type_list.append(UserQuota.CUSTOM_STORAGE)

    with transaction.atomic():
        for storage_type in storage_type_list:
            used = used_quota(user._id, storage_type)
            try:
                if check_select_for_update():
                    user_quota = UserQuota.objects.filter(
                        user=user,
                        storage_type=storage_type,
                    ).select_for_update().get()
                else:
                    user_quota = UserQuota.objects.get(
                        user=user,
                        storage_type=storage_type,
                    )
                user_quota.used = used
                user_quota.save()
            except UserQuota.DoesNotExist:
                UserQuota.objects.create(
                    user=user,
                    storage_type=storage_type,
                    max_quota=api_settings.DEFAULT_MAX_QUOTA,
                    used=used,
                )

def all_users(request, **kwargs):
    c = 0
    for osf_user in OSFUser.objects.exclude(deleted__isnull=False):
        calculate_quota(osf_user)
        c += 1
    return JsonResponse({
        'status': 'OK',
        'message': str(c) + ' users\' quota successfully recalculated!'
    })

def user(request, guid, **kwargs):
    user = OSFUser.load(guid)
    if user is None:
        return JsonResponse({
            'status': 'failed',
            'message': 'User not found.'
        }, status=404)
    calculate_quota(user)
    return JsonResponse({
        'status': 'OK',
        'message': 'User\'s quota successfully recalculated!'
    })
