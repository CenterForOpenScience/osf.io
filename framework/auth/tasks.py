from datetime import datetime
import itertools
import logging

from lxml import etree
import pytz
import requests

from framework import sentry
from framework.celery_tasks import app as celery_app
from website.settings import (DATE_LAST_LOGIN_THROTTLE_DELTA, EXTERNAL_IDENTITY_PROFILE,
                              ORCID_PUBLIC_API_V3_URL, ORCID_PUBLIC_API_ACCESS_TOKEN,
                              ORCID_PUBLIC_API_REQUEST_TIMEOUT, ORCID_RECORD_ACCEPT_TYPE,
                              ORCID_RECORD_EDUCATION_PATH, ORCID_RECORD_EMPLOYMENT_PATH)


logger = logging.getLogger(__name__)


@celery_app.task()
def update_user_from_activity(user_id, login_time, cas_login=False, updates=None):
    from osf.models import OSFUser
    if not updates:
        updates = {}
    if isinstance(login_time, float):
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
    from osf.models import OSFUser
    user = OSFUser.load(user_id)
    if not user or not verify_user_orcid_id(user, orcid_id):
        # This should not happen as long as this task is called at the right place at the right time.
        error_message = f'Invalid ORCiD ID [{orcid_id}] for [{user_id}]' if user else f'User [{user_id}] Not Found'
        logger.error(error_message)
        sentry.log_message(error_message)
        return
    institution = check_institution_affiliation(orcid_id)
    if institution:
        logger.info(f'Eligible institution affiliation has been found for ORCiD SSO user: '
                    f'institution=[{institution._id}], user=[{user_id}], orcid_id=[{orcid_id}]')
        user.add_or_update_affiliated_institution(institution=institution, sso_identity=orcid_id)


def verify_user_orcid_id(user, orcid_id):
    """Verify that the given ORCiD ID is verified for the given user.
    """
    provider = EXTERNAL_IDENTITY_PROFILE.get('OrcidProfile')
    status = user.external_identity.get(provider, {}).get(orcid_id, None)
    return status == 'VERIFIED'


def check_institution_affiliation(orcid_id):
    """Check user's public ORCiD record and return eligible institution affiliations.

    Note: Current implementation only support one affiliation (i.e. loop returns once eligible
          affiliation is found, which improves performance). In the future, if we have multiple
          institutions using this feature, we can update the loop easily.
    """
    from osf.models import Institution
    from osf.models.institution import IntegrationType
    employment_source_list = get_orcid_employment_sources(orcid_id)
    education_source_list = get_orcid_education_sources(orcid_id)
    via_orcid_institutions = Institution.objects.filter(
        delegation_protocol=IntegrationType.AFFILIATION_VIA_ORCID.value,
        is_deleted=False
    )
    # Check both employment and education records
    for source in itertools.chain(employment_source_list, education_source_list):
        # Check source against all "affiliation-via-orcid" institutions
        for institution in via_orcid_institutions:
            if source == institution.orcid_record_verified_source:
                logger.debug(f'Institution has been found with matching source: '
                             f'institution=[{institution._id}], source=[{source}], orcid_id=[{orcid_id}]')
                return institution
    logger.debug(f'No institution with matching source has been found: orcid_id=[{orcid_id}]')
    return None


def get_orcid_employment_sources(orcid_id):
    """Retrieve employment records for the given ORCiD ID.
    """
    employment_data = orcid_public_api_make_request(ORCID_RECORD_EMPLOYMENT_PATH, orcid_id)
    source_list = []
    if employment_data is not None:
        affiliation_groups = employment_data.findall('{http://www.orcid.org/ns/activities}affiliation-group')
        for affiliation_group in affiliation_groups:
            employment_summary = affiliation_group.find('{http://www.orcid.org/ns/employment}employment-summary')
            source = employment_summary.find('{http://www.orcid.org/ns/common}source')
            source_name = source.find('{http://www.orcid.org/ns/common}source-name')
            source_list.append(source_name.text)
    return source_list


def get_orcid_education_sources(orcid_id):
    """Retrieve education records for the given ORCiD ID.
    """
    education_data = orcid_public_api_make_request(ORCID_RECORD_EDUCATION_PATH, orcid_id)
    source_list = []
    if education_data is not None:
        affiliation_groups = education_data.findall('{http://www.orcid.org/ns/activities}affiliation-group')
        for affiliation_group in affiliation_groups:
            education_summary = affiliation_group.find('{http://www.orcid.org/ns/education}education-summary')
            source = education_summary.find('{http://www.orcid.org/ns/common}source')
            source_name = source.find('{http://www.orcid.org/ns/common}source-name')
            source_list.append(source_name.text)
    return source_list


def orcid_public_api_make_request(path, orcid_id):
    """Make the ORCiD public API request and returned a deserialized response.
    """
    request_url = ORCID_PUBLIC_API_V3_URL + orcid_id + path
    headers = {
        'Accept': ORCID_RECORD_ACCEPT_TYPE,
        'Authorization': f'Bearer {ORCID_PUBLIC_API_ACCESS_TOKEN}',
    }
    try:
        response = requests.get(request_url, headers=headers, timeout=ORCID_PUBLIC_API_REQUEST_TIMEOUT)
    except Exception as e:
        error_message = f'ORCiD public API request has encountered an exception: url=[{request_url}]'
        logger.error(error_message)
        sentry.log_message(error_message)
        sentry.log_exception(e)
        return None
    if response.status_code != 200:
        error_message = f'ORCiD public API request has failed: url=[{request_url}], ' \
                        f'status=[{response.status_code}], response = [{response.content}]'
        logger.error(error_message)
        sentry.log_message(error_message)
        return None
    try:
        xml_data = etree.XML(response.content)
    except Exception as e:
        error_message = 'Fail to read and parse ORCiD record response as XML'
        logger.error(error_message)
        sentry.log_message(error_message)
        sentry.log_exception(e)
        return None
    return xml_data
