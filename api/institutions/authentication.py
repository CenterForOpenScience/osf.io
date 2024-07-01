import json
import uuid
import logging

import jwe
import jwt
import waffle

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from addons.osfstorage.models import UserSettings as OSFStorageUserSettings
from addons.osfstorage.models import Region

from api.base.authentication import drf
from api.base import exceptions, settings

from framework import sentry
from framework.auth import get_or_create_institutional_user

from osf import features
from osf.exceptions import InstitutionAffiliationStateError
from osf.models import Institution
from osf.models.institution import SsoFilterCriteriaAction

from website.mails import send_mail, WELCOME_OSF4I, DUPLICATE_ACCOUNTS_OSF4I, ADD_SSO_EMAIL_OSF4I
from website.settings import OSF_SUPPORT_EMAIL, DOMAIN

logger = logging.getLogger(__name__)

# This map defines how to find the secondary institution which uses SSO of a primary one. Each map
# entry has the following format.
#
#    '<ID of the primary institution A>': {
#        'attribute_name': '<the attribute name for identifying secondary institutions>',
#        'criteria_action': '<the action to perform between the attribute value and criteria value',
#        'criteria_value': '<the value that>
#        'institution_id': 'the ID of the secondary institution',
#    }
# For now, this map is temporarily defined here but will be moved to settings or be re-implemented
# in model via relationships later. In addition, we should be able to make the attribute name fixed
# since CAS can normalize them into "sharedSsoFilter" ahead of time.
#
INSTITUTION_SHARED_SSO_MAP = {
    'brown': {
        'attribute_name': 'isMemberOf',
        'criteria_action': SsoFilterCriteriaAction.EQUALS_TO.value,
        'criteria_value': 'thepolicylab',
        'institution_id': 'thepolicylab',
    },
    'fsu': {
        'attribute_name': 'userRoles',
        'criteria_action': SsoFilterCriteriaAction.CONTAINS.value,
        'criteria_value': 'FSU_OSF_MAGLAB',
        'institution_id': 'nationalmaglab',
    },
}

# A map that defines whether to allow an institutional user to access OSF via SSO. For each entry,
# the key is the institution ID and the (entry) value is the expected value of the filter attribute
# "selectiveSsoFilter". For local testing w/ Postman and CAS, add `'fake-saml-type-2': 'allowOsf'`.
INSTITUTION_SELECTIVE_SSO_MAP = {
    'uom': {
        'criteria_action': SsoFilterCriteriaAction.EQUALS_TO.value,
        'criteria_value': 'http://directory.manchester.ac.uk/epe/3rdparty/osf',
    },
    'yls': {
        'criteria_action': SsoFilterCriteriaAction.IN.value,
        'criteria_value': ['Yes', 'yes', 'y'],
    },
}


class InstitutionAuthentication(BaseAuthentication):
    """A dedicated authentication class for view ``InstitutionAuth``.

    The ``InstitutionAuth`` view and the ``InstitutionAuthentication`` class are only and should
    only be used by OSF CAS for institution login. Changing this class and related tests may break
    the institution login feature. Please check with @longzeC / @mattF / @brianG before making any
    changes.
    """

    media_type = 'text/plain'

    def authenticate(self, request):
        """
        Handle CAS institution authentication request.

        Note: If authentication fails, HTTP 403 Forbidden is returned no matter what type of the
        exception is raised. In this method, we use ``AuthenticationFailed`` when the payload is
        not correctly encrypted or encoded since it is the "authentication" between CAS and this
        endpoint. We use `PermissionDenied` for all other exceptions that happens afterwards.

        Expected JWT ``data`` payload format in JSON:

        .. highlight:: json
        .. code-block:: python

            {
                "provider": {
                    "idp": "",
                    "id": "",
                    "user": {
                        "ssoIdentity": "",
                        "ssoEmail": "",
                        "fullname": "",
                        "familyName": "",
                        "givenName": "",
                        "middleNames": "",
                        "suffix": "",
                        "department": "",
                        "isMemberOf": "",
                        "selectiveSsoFilter": "",
                    }
                }
            }

        :param request: the POST request
        :return: user, None if authentication succeed
        :raises: AuthenticationFailed or PermissionDenied if authentication fails
        """

        # Verify / decrypt / decode the payload
        try:
            payload = jwt.decode(
                jwe.decrypt(request.body, settings.JWE_SECRET),
                settings.JWT_SECRET,
                options={'verify_exp': False},
                algorithms=['HS256'],
            )
        except (jwt.InvalidTokenError, TypeError, jwe.exceptions.MalformedData):
            raise AuthenticationFailed(detail='InstitutionSsoRequestNotAuthorized')

        # Load institution and user data
        data = json.loads(payload['data'])
        provider = data['provider']
        institution = Institution.load(provider['id'])
        if not institution:
            message = f'Institution SSO Error: invalid institution ID [{provider["id"]}]'
            logger.error(message)
            sentry.log_message(message)
            raise PermissionDenied(detail='InstitutionSsoInvalidInstitution')

        sso_identity = provider['user'].get('ssoIdentity')
        sso_identity = sso_identity.strip() if sso_identity else None

        sso_email = provider['user'].get('ssoEmail')
        fullname = provider['user'].get('fullname')
        given_name = provider['user'].get('givenName')
        family_name = provider['user'].get('familyName')
        middle_names = provider['user'].get('middleNames')
        suffix = provider['user'].get('suffix')
        department = provider['user'].get('department')
        selective_sso_filter = provider['user'].get('selectiveSsoFilter')

        # Check selective login first
        if provider['id'] in INSTITUTION_SELECTIVE_SSO_MAP:
            selective_sso_map = INSTITUTION_SELECTIVE_SSO_MAP[provider['id']]
            criteria_action = selective_sso_map.get('criteria_action')
            criteria_value = selective_sso_map.get('criteria_value')
            allow_sso = False
            # Selective SSO: login not allowed
            if criteria_action == SsoFilterCriteriaAction.EQUALS_TO.value and selective_sso_filter == criteria_value:
                allow_sso = True
            if criteria_action == SsoFilterCriteriaAction.IN.value and selective_sso_filter in criteria_value:
                allow_sso = True
            if not allow_sso:
                message = f'Institution SSO Error: user is not allowed for institution SSO due to selective SSO ' \
                          f'rules [sso_email={sso_email}, sso_identity={sso_identity}, institution={institution._id}]'
                logger.error(message)
                sentry.log_message(message)
                raise PermissionDenied(detail='InstitutionSsoSelectiveLoginDenied')
            # Selective SSO: login allowed
            logger.info(
                f'Institution SSO: selective SSO verified for user '
                f'[sso_email={sso_email}, sso_identity={sso_identity}, institution={institution._id}]',
            )

        # Check secondary institutions which uses the SSO of primary ones
        secondary_institution = None
        if provider['id'] in INSTITUTION_SHARED_SSO_MAP:
            switch_map = INSTITUTION_SHARED_SSO_MAP[provider['id']]
            attribute_name = switch_map.get('attribute_name')
            criteria_action = switch_map.get('criteria_action')
            criteria_value = switch_map.get('criteria_value')
            attribute_value = provider['user'].get(attribute_name)
            # Check affiliation filter criteria and retrieve the secondary institution ID
            secondary_institution_id = None
            if criteria_action == SsoFilterCriteriaAction.EQUALS_TO.value:
                secondary_institution_id = switch_map.get('institution_id') if criteria_value == attribute_value else None
            elif criteria_action == SsoFilterCriteriaAction.CONTAINS.value:
                secondary_institution_id = switch_map.get('institution_id') if criteria_value in attribute_value else None
            else:
                message = f'Institution Shared SSO Error: invalid affiliation filter criteria action ' \
                          f'[action={criteria_action}, primary={provider["id"]}, ' \
                          f'sso_email={sso_email}, sso_identity={sso_identity}]'
                logger.error(message)
                sentry.log_message(message)
            # Attempt to load the secondary institution by ID
            if secondary_institution_id:
                logger.info(
                    f'Institution Shared SSO Eligible: '
                    f'[primary={provider["id"]}, secondary={secondary_institution_id}, '
                    f'filter=[{attribute_name}: {attribute_value} {criteria_action} {criteria_value}], '
                    f'sso_email={sso_email}, sso_identity={sso_identity}]',
                )
                secondary_institution = Institution.load(secondary_institution_id)
                if not secondary_institution:
                    # Log errors and inform Sentry but do not raise an exception if OSF fails
                    # to load the secondary institution from database
                    message = f'Institution Shared SSO Warning: ' \
                              f'invalid secondary institution, use the primary one instead ' \
                              f'[primary={provider["id"]}, second={secondary_institution_id}, ' \
                              f'sso_email={sso_email}, sso_identity={sso_identity}]'
                    logger.error(message)
                    sentry.log_message(message)
            else:
                # SSO from primary institution only
                logger.info(
                    f'Institution Shared SSO Not Eligible: use the primary institution only'
                    f'[primary={provider["id"]}, secondary=None, '
                    f'sso_email={sso_email}, sso_identity={sso_identity}]',
                )

        # Use given name and family name to build full name if it is not provided
        if given_name and family_name and not fullname:
            fullname = given_name + ' ' + family_name

        # Non-empty full name is required. Fail the auth and inform sentry if not provided.
        if not fullname:
            message = f'Institution SSO Error: missing full name ' \
                      f'[sso_email={sso_email}, sso_identity={sso_identity}, institution={provider["id"]}]'
            logger.error(message)
            sentry.log_message(message)
            raise PermissionDenied(detail='InstitutionSsoMissingUserNames')

        # Attempt to find an existing user that matches the email(s) provided via SSO. Create a new one if not found.
        # If a user is found, it is possible that the user is inactive (e.g. unclaimed, disabled, unconfirmed, etc.).
        # If a new user is created, the user object is confirmed but not registered (i.e. inactive until registered).
        try:
            user, is_created, duplicate_user, email_to_add, identity_to_add = get_or_create_institutional_user(
                fullname,
                sso_email,
                sso_identity,
                institution,
            )
        except InstitutionAffiliationStateError:
            message = f'Institution SSO Error: duplicate SSO identity {sso_identity} found for institution ' \
                      f'[{institution._id}]. More info: SSO email is [{sso_email}]'
            sentry.log_message(message)
            logger.error(message)
            raise PermissionDenied(detail='InstitutionSsoDuplicateIdentity')

        # Existing but inactive users need to be either "activated" or failed the auth
        activation_required = False
        new_password_required = False
        sso_user_info = f'[guid={user._id}, username={user.username}, sso_email={sso_email}, ' \
                        f'sso_identity={sso_identity}, institution_id={institution._id}]'
        if not is_created:
            try:
                drf.check_user(user)
                logger.info(f'Institution SSO: user status - active {sso_user_info}')
            except exceptions.UnclaimedAccountError:
                # Unclaimed user (i.e. a user that has been added as an unregistered contributor)
                user.unclaimed_records = {}
                activation_required = True
                # Unclaimed users have an unusable password when being added as an unregistered
                # contributor. Thus, a random usable password must be assigned during activation.
                new_password_required = True
                logger.warning(f'Institution SSO: user status - unclaimed contributor {sso_user_info}')
            except exceptions.UnconfirmedAccountError:
                if user.has_usable_password():
                    # Unconfirmed user from default username / password signup
                    user.email_verifications = {}
                    activation_required = True
                    # Unconfirmed users already have a usable password set by the creator during
                    # sign-up. However, it must be overwritten by a new random one so the creator
                    # (if he is not the real person) can not access the account after activation.
                    new_password_required = True
                    logger.warning(f'Institution SSO: user status - unconfirmed user {sso_user_info}')
                else:
                    # Login take-over has not been implemented for unconfirmed user created via
                    # external IdP login (ORCiD).
                    message = f'Institution SSO Error: SSO is not eligible ' \
                              f'for an unconfirmed account {sso_user_info} created via ORCiD login'
                    sentry.log_message(message)
                    logger.error(message)
                    raise PermissionDenied(detail='InstitutionSsoAccountInactive')
            except exceptions.DeactivatedAccountError:
                # Deactivated user: login is not allowed for deactivated users
                message = f'Institution SSO Error: SSO is not eligible for a deactivated account {sso_user_info}'
                sentry.log_message(message)
                logger.error(message)
                raise PermissionDenied(detail='InstitutionSsoAccountInactive')
            except exceptions.MergedAccountError:
                # Merged user: this shouldn't happen since merged users do not have an email
                message = f'Institution SSO Error: SSO is not eligible for a merged account {sso_user_info}'
                sentry.log_message(message)
                logger.error(message)
                raise PermissionDenied(detail='InstitutionSsoAccountInactive')
            except exceptions.InvalidAccountError:
                # Other invalid status: this shouldn't happen unless the user happens to be in a
                # temporary state. Such state requires more updates before the user can be saved
                # to the database.
                message = f'Institution SSO Error: SSO is not eligible for an invalid account {sso_user_info}'
                sentry.log_message(message)
                logger.error(message)
                raise PermissionDenied(detail='InstitutionSsoAccountInactive')
        else:
            logger.info(f'Institution SSO: new user created {sso_user_info}')

        # Both created and activated accounts need to be updated and registered
        if is_created or activation_required:

            if given_name:
                user.given_name = given_name
            if family_name:
                user.family_name = family_name
            if middle_names:
                user.middle_names = middle_names
            if suffix:
                user.suffix = suffix

            # Users claimed or confirmed via institution SSO should have their full name updated
            if activation_required:
                user.fullname = fullname

            user.update_date_last_login()

            # Register and save user
            password = str(uuid.uuid4()) if new_password_required else None
            user.register(sso_email, password=password)
            user.save()

            # Send confirmation email for all three: created, confirmed and claimed
            send_mail(
                to_addr=user.username,
                mail=WELCOME_OSF4I,
                user=user,
                domain=DOMAIN,
                osf_support_email=OSF_SUPPORT_EMAIL,
                storage_flag_is_active=waffle.flag_is_active(request, features.STORAGE_I18N),
            )

        # Add the email to the user's account if it is identified by the eppn
        if email_to_add:
            assert not is_created and email_to_add == sso_email
            user.emails.create(address=email_to_add)
            send_mail(
                to_addr=user.username,
                mail=ADD_SSO_EMAIL_OSF4I,
                user=user,
                email_to_add=email_to_add,
                domain=DOMAIN,
                osf_support_email=OSF_SUPPORT_EMAIL,
            )

        # Inform the user that a potential duplicate account is found
        # Remove sso identity from the duplicate user since it will be added to the authn user
        # Note: DON't automatically merge accounts. MUST leave the decision to the user.
        if duplicate_user:
            assert not is_created and email_to_add is None
            duplicate_user.remove_sso_identity_from_affiliation(institution)
            if secondary_institution:
                duplicate_user.remove_sso_identity_from_affiliation(secondary_institution)
            send_mail(
                to_addr=user.username,
                mail=DUPLICATE_ACCOUNTS_OSF4I,
                user=user,
                duplicate_user=duplicate_user,
                domain=DOMAIN,
                osf_support_email=OSF_SUPPORT_EMAIL,
            )

        # Affiliate the user to the primary institution if not previously affiliated
        user.add_or_update_affiliated_institution(
            institution,
            sso_identity=identity_to_add,
            sso_mail=sso_email,
            sso_department=department,
        )

        # Affiliate the user to the secondary institution if not previously affiliated
        if secondary_institution:
            user.add_or_update_affiliated_institution(
                secondary_institution,
                sso_identity=identity_to_add,
                sso_mail=sso_email,
                sso_department=department,
            )

        # Storage region is only updated if the user is created via institutional SSO; the region will be set to the
        # institution's preferred one if the user's current region is not in the institution's default region list.
        if is_created:
            user_settings = OSFStorageUserSettings.objects.get(owner=user)
            institution_region_list = institution.storage_regions.all()
            if institution_region_list and user_settings.default_region not in institution_region_list:
                try:
                    user_settings.default_region = institution_region_list.get(institutionstorageregion__is_preferred=True)
                    user_settings.save()
                except Region.DoesNotExist:
                    message = f'Institution SSO Warning: Institution {institution._id} does not have a preferred default region'
                    sentry.log_message(message)
                    logger.error(message)

        return user, None
