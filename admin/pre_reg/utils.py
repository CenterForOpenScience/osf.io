from django.db.models.functions import Concat
from django.db.models import Value

from admin.common_auth.models import MyUser


def get_prereg_reviewers():
    return MyUser.objects.filter(
        groups__name='prereg_group'
    ).annotate(
        fuller_name=Concat('first_name', Value(' '), 'last_name')
    ).values_list(
        'email', 'fuller_name'
    )
