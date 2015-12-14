import itertools

from django.contrib.auth import models

def get_prereg_reviewers():
    return itertools.chain(
        ((None, 'None'), ),
        (
            (u.email, u.full_name)
            for u in models.Group.objects.get(name='prereg_group').user_set.all()
        )
    )
