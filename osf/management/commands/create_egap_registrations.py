from datetime import datetime as dt

from django.core.management.base import BaseCommand
import django
django.setup()

from framework.auth.core import Auth
from osf import exceptions
from osf.models import DraftRegistration, OSFUser
from osf.utils.permissions import ADMIN

def register_silently(draft_registration, auth, sanction_type, external_registered_date, embargo_end_date):
    try:
        registration = draft_registration.register(auth, save=True)
    except exceptions.NodeStateError as err:
        raise exceptions.ValidationError(err)

    registration.external_registered_date = external_registered_date

    if sanction_type == 'Embargo':
        try:
            registration.embargo_registration(auth.user, embargo_end_date)
        except exceptions.ValidationError as err:
            raise exceptions.ValidationError(err.message)
    else:
        try:
            registration.require_approval(auth.user)
        except exceptions.NodeStateError as err:
            raise exceptions.ValidationError(err)

    registration.save()

def main():
    # Retrieve all EGAP Draft Registrations
    egap_draft_registrations = DraftRegistration.objects.filter(registration_schema__name='EGAP Registration')

    # Retrieve EGAP Admin (Greg?)
    egap_author = OSFUser.objects.get(username='uday@cos.io')
    egap_auth = Auth(egap_author)

    for draft_registration in egap_draft_registrations:
        project = draft_registration.branched_from
        draft_registration_metadata = draft_registration.registration_metadata

        # Retrieve EGAP registration date and potential embargo go-public date
        egap_registration_date_string = draft_registration_metadata['q4']['value']
        egap_embargo_public_date_string = draft_registration_metadata['q12']['value']

        egap_registration_date = dt.strptime(egap_registration_date_string, '%m/%d/%Y')
        egap_embargo_public_date = dt.strptime(egap_embargo_public_date_string, '%m/%d/%Y')

        sanction_type = 'RegistrationApproval'
        if egap_embargo_public_date > dt.today():
            sanction_type = 'Embargo'

        register_silently(draft_registration, egap_auth, sanction_type, egap_registration_date, egap_embargo_public_date)

        # Update contributors on project to Admin
        contributors = project.contributor_set.all()
        for contributor in contributors:
            if contributor.user == egap_author:
                pass
            else:
                project.update_contributor(contributor.user, permission=ADMIN, visible=True, auth=egap_auth, save=True)


class Command(BaseCommand):
    help = '''Creates the EGAP Registrations and approves them while suppressing emails.'''

    def handle(self, *args, **options):
        main()
