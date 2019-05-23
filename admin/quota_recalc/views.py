from django.http import JsonResponse

from api.base import settings as api_settings
from osf.models import OSFUser, UserQuota
from website.util.quota import used_quota


def calculate_quota(user):
    used = used_quota(user._id, UserQuota.NII_STORAGE)
    try:
        user_quota = UserQuota.objects.get(
            user=user,
            storage_type=UserQuota.NII_STORAGE,
        )
        user_quota.used = used
        user_quota.save()
    except UserQuota.DoesNotExist:
        UserQuota.objects.create(
            user=user,
            storage_type=UserQuota.NII_STORAGE,
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
