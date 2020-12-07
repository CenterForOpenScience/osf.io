"""
  Fix bad sanction states introduced by https://github.com/CenterForOpenScience/osf.io/pull/3919

    python3 manage.py update_old_sanction_states
"""
from django.core.management.base import BaseCommand

from osf.models import Embargo, Retraction


def update_old_sanction_states():
    '''Fix out-of-date states for Embargo and Retraction objects.

    https://github.com/CenterForOpenScience/osf.io/pull/3919 homogenized a lot
    of the code behind the Embargo and Retraction objecs as part of introducing
    the RegistrationApproval. It abruptly changed the acceptable states for
    these models without updating existing values for them. This command
    will bring them up-to-date.
    '''

    Embargo.objects.filter(state__iexact='active').update(state=Embargo.APPROVED)
    Embargo.objects.filter(state__iexact='cancelled').update(state=Embargo.REJECTED)
    Retraction.objects.filter(state__iexact='retracted').update(state=Retraction.APPROVED)
    Retraction.objects.filter(state__iexact='pending').update(state=Retraction.UNAPPROVED)
    Retraction.objects.filter(state__iexact='cancelled').update(state=Retraction.REJECTED)


class Command(BaseCommand):

    def handle(self, *args, **options):
        update_old_sanction_states()
