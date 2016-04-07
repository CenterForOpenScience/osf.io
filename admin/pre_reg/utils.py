from django.db.models.functions import Concat
from django.db.models import Value

from admin.common_auth.models import MyUser


def get_prereg_reviewers():
    # Note - fixes django.db.utils.OperationalError: no such table' error if ever one erases a db table and tries to remigrate
    try:
        return MyUser.objects.filter(
            groups__name='prereg_group'
        ).annotate(
            fuller_name=Concat('first_name', Value(' '), 'last_name')
        ).values_list(
            'email', 'fuller_name'
        )
    except Exception:
        return []
