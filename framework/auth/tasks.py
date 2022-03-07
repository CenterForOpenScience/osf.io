from datetime import datetime
import pytz

from framework.celery_tasks import app as celery_app
from osf.models import Institution, OSFUser
from osf.models.institution import IntegrationType
from website.settings import DATE_LAST_LOGIN_THROTTLE_DELTA, EXTERNAL_IDENTITY_PROFILE


@celery_app.task()
def update_user_from_activity(user_id, login_time, cas_login=False, updates=None):
    from osf.models import OSFUser
    if not updates:
        updates = {}
    if type(login_time) == float:
        login_time = datetime.fromtimestamp(login_time, pytz.UTC)
    user = OSFUser.load(user_id)
    should_save = False
    if not user.date_last_login or user.date_last_login < login_time - DATE_LAST_LOGIN_THROTTLE_DELTA:
        user.update_date_last_login(login_time)
        should_save = True
    if cas_login:
        user.clean_email_verifications()
        user.update_affiliated_institutions_by_email_domain()
        if 'accepted_terms_of_service' in updates:
            user.accepted_terms_of_service = updates['accepted_terms_of_service']
        if 'verification_key' in updates:
            user.verification_key = updates['verification_key']
        should_save = True
    if should_save:
        user.save()


@celery_app.task()
def update_affiliation_for_orcid_sso_users(user_id, orcid_id):
    """This is an asynchronous task that runs during CONFIRMED ORCiD SSO logins and makes eligible
    institution affiliations.
    """
    user = OSFUser.load(user_id)
    if not user or not verify_user_orcid_id(user, orcid_id):
        # This should not happen as long as this task is called at the right place at the right time.
        # TODO: Log errors, raise exceptions and inform Sentry
        return
    institution = check_institution_affiliation(orcid_id)
    if institution and not user.is_affiliated_with_institution(institution):
        user.affiliated_institutions.add(institution)
        user.save()


def verify_user_orcid_id(user, orcid_id):
    """Verify that the given ORCiD ID is verified for the given user.
    """
    provider = EXTERNAL_IDENTITY_PROFILE.get('OrcidProfile')
    status = user.external_identity.get(provider, {}).get(orcid_id, None)
    return True if status and status == 'VERIFIED' else False


def check_institution_affiliation(orcid_id):
    """Check user's public ORCiD record and return eligible institution affiliations.

    Note: Current implementation only support one affiliation (i.e. loop returns once eligible
          affiliation is found, which improves performance). In the future, if we have multiple
          institutions using this feature, we can update the loop easily.
    """
    employment_records = get_orcid_employment_records(orcid_id)
    education_records = get_orcid_education_records(orcid_id)
    via_orcid_institutions = Institution.objects.filter(
        delegation_protocol=IntegrationType.AFFILIATION_VIA_ORCID.value,
        is_deleted=False
    )
    # Check both employment and education records
    for record in employment_records + education_records:
        source = record.get('source')
        if not source:
            continue
        # check source against all "affiliation-via-orcid" institutions
        for institution in via_orcid_institutions:
            if source == institution.orcid_record_verified_source:
                return institution
    return None


def get_orcid_employment_records(orcid_id):
    """Retrieve employment records for the given ORCiD ID.
    """
    # TODO: this will be implemented in ENG-3621
    return []


def get_orcid_education_records(orcid_id):
    """Retrieve education records for the given ORCiD ID.
    """
    # TODO: this will be implemented in ENG-3621
    return []
