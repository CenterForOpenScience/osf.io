import json
import uuid
import logging

import jwe
import jwt
import waffle

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from api.base.authentication import drf
from api.base import exceptions, settings

from framework import sentry
from framework.auth import get_or_create_user

from osf import features
from osf.models import Institution
from osf.models.institution import SharedSsoAffiliationFilterCriteriaAction

from website.mails import send_mail, WELCOME_OSF4I
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
        'criteria_action': SharedSsoAffiliationFilterCriteriaAction.EQUALS_TO.value,
        'criteria_value': 'thepolicylab',
        'institution_id': 'thepolicylab',
    },
    'fsu': {
        'attribute_name': 'userRoles',
        'criteria_action': SharedSsoAffiliationFilterCriteriaAction.CONTAINS.value,
        'criteria_value': 'FSU_OSF_MAGLAB',
        'institution_id': 'nationalmaglab',
    },
}

# A map that defines whether to allow an institutional user to access OSF via SSO. For each entry,
# the key is the institution ID and the (entry) value is the expected value of the filter attribute
# "selectiveSsoFilter". For local testing w/ Postman and CAS, add `'fake-saml-type-2': 'allowOsf'`.
INSTITUTION_SELECTIVE_SSO_MAP = {
    'uom': 'http://directory.manchester.ac.uk/epe/3rdparty/osf',
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

        The JWT `data` payload is expected in the following structure:
        {
            "provider": {
                "idp": "",
                "id": "",
                "user": {
                    "username": "",
                    "fullname": "",
                    "familyName": "",
                    "givenName": "",
                    "middleNames": "",
                    "suffix": "",
                    "department": "",
                    "isMemberOf": "",  # Shared SSO
                    "selectiveSsoFilter": "",  # Selective SSO
                }
            }
        }

        Note that if authentication failed, HTTP 403 Forbidden is returned no matter what type of
        exception is raised. In this method, we use `AuthenticationFailed` when the payload is not
        correctly encrypted/encoded since it is the "authentication" between CAS and this endpoint.
        We use `PermissionDenied` for all other exceptions that happened afterwards.

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
                algorithm='HS256',
            )
        except (jwt.InvalidTokenError, TypeError, jwe.exceptions.MalformedData):
            raise AuthenticationFailed(detail='InstitutionSsoRequestNotAuthorized')

        # Load institution and user data
        data = json.loads(payload['data'])
        provider = data['provider']
        institution = Institution.load(provider['id'])
        if not institution:
            message = 'Institution SSO Error: invalid institution ID [{}]'.format(provider['id'])
            logger.error(message)
            sentry.log_message(message)
            raise PermissionDenied(detail='InstitutionSsoInvalidInstitution')
        username = provider['user'].get('username')
        fullname = provider['user'].get('fullname')
        given_name = provider['user'].get('givenName')
        family_name = provider['user'].get('familyName')
        middle_names = provider['user'].get('middleNames')
        suffix = provider['user'].get('suffix')
        department = provider['user'].get('department')
        selective_sso_filter = provider['user'].get('selectiveSsoFilter')

        # Check selective login first
        if provider['id'] in INSTITUTION_SELECTIVE_SSO_MAP:
            if selective_sso_filter != INSTITUTION_SELECTIVE_SSO_MAP[provider['id']]:
                message = f'Institution SSO Error: user [email={username}] is not allowed for ' \
                          f'institution SSO [id={institution._id}] due to selective SSO rules'
                logger.error(message)
                sentry.log_message(message)
                raise PermissionDenied(detail='InstitutionSsoSelectiveNotAllowed')
            logger.info(
                f'Institution SSO: selective SSO verified for user [email={username}] '
                f'at institution [id={institution._id}]',
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
            if criteria_action == SharedSsoAffiliationFilterCriteriaAction.EQUALS_TO.value:
                secondary_institution_id = switch_map.get('institution_id') if criteria_value == attribute_value else None
            elif criteria_action == SharedSsoAffiliationFilterCriteriaAction.CONTAINS.value:
                secondary_institution_id = switch_map.get('institution_id') if criteria_value in attribute_value else None
            else:
                message = 'Institution Shared SSO Error: invalid affiliation filter criteria action [{}]; ' \
                          'primary=[{}], username=[{}]'.format(criteria_action, provider['id'], username)
                logger.error(message)
                sentry.log_message(message)
            # Attempt to load the secondary institution by ID
            if secondary_institution_id:
                logger.info(
                    'Institution Shared SSO Eligible: primary=[{}], secondary=[{}], '
                    'filter=[{}: {} {} {}], username=[{}]'.format(
                        provider['id'], secondary_institution_id, attribute_name,
                        attribute_value, criteria_action, criteria_value, username,
                    ),
                )
                secondary_institution = Institution.load(secondary_institution_id)
                if not secondary_institution:
                    # Log errors and inform Sentry but do not raise an exception if OSF fails
                    # to load the secondary institution from database
                    message = 'Institution Shared SSO Warning: invalid secondary institution [{}], primary=[{}], ' \
                              'username=[{}]'.format(secondary_institution_id, provider['id'], username)
                    logger.error(message)
                    sentry.log_message(message)
            else:
                # SSO from primary institution only
                logger.info('Institution SSO: primary=[{}], secondary=[None], '
                            'username=[{}]'.format(provider['id'], username))

        # Use given name and family name to build full name if it is not provided
        if given_name and family_name and not fullname:
            fullname = given_name + ' ' + family_name

        # Non-empty full name is required. Fail the auth and inform sentry if not provided.
        if not fullname:
            message = 'Institution SSO Error: missing fullname ' \
                      'for user [{}] from institution [{}]'.format(username, provider['id'])
            logger.error(message)
            sentry.log_message(message)
            raise PermissionDenied(detail='InstitutionSsoMissingUserNames')

        # Get an existing user or create a new one. If a new user is created, the user object is
        # confirmed but not registered,which is temporarily of an inactive status. If an existing
        # user is found, it is also possible that the user is inactive (e.g. unclaimed, disabled,
        # unconfirmed, etc.).
        user, created = get_or_create_user(fullname, username, reset_password=False)

        # Existing but inactive users need to be either "activated" or failed the auth
        activation_required = False
        new_password_required = False
        if not created:
            try:
                drf.check_user(user)
                logger.info('Institution SSO: active user [{}]'.format(username))
            except exceptions.UnclaimedAccountError:
                # Unclaimed user (i.e. a user that has been added as an unregistered contributor)
                user.unclaimed_records = {}
                activation_required = True
                # Unclaimed users have an unusable password when being added as an unregistered
                # contributor. Thus a random usable password must be assigned during activation.
                new_password_required = True
                logger.warning('Institution SSO: unclaimed contributor [{}]'.format(username))
            except exceptions.UnconfirmedAccountError:
                if user.has_usable_password():
                    # Unconfirmed user from default username / password signup
                    user.email_verifications = {}
                    activation_required = True
                    # Unconfirmed users already have a usable password set by the creator during
                    # sign-up. However, it must be overwritten by a new random one so the creator
                    # (if he is not the real person) can not access the account after activation.
                    new_password_required = True
                    logger.warning('Institution SSO: unconfirmed user [{}]'.format(username))
                else:
                    # Login take-over has not been implemented for unconfirmed user created via
                    # external IdP login (ORCiD).
                    message = 'Institution SSO Error: SSO is not eligible for an unconfirmed account [{}] ' \
                              'created via IdP login'.format(username)
                    sentry.log_message(message)
                    logger.error(message)
                    raise PermissionDenied(detail='InstitutionSsoAccountNotConfirmed')
            except exceptions.DeactivatedAccountError:
                # Deactivated user: login is not allowed for deactivated users
                message = 'Institution SSO Error: SSO is not eligible for a deactivated account: [{}]'.format(username)
                sentry.log_message(message)
                logger.error(message)
                raise PermissionDenied(detail='InstitutionSsoAccountDisabled')
            except exceptions.MergedAccountError:
                # Merged user: this shouldn't happen since merged users do not have an email
                message = 'Institution SSO Error: SSO is not eligible for a merged account: [{}]'.format(username)
                sentry.log_message(message)
                logger.error(message)
                raise PermissionDenied(detail='InstitutionSsoAccountMerged')
            except exceptions.InvalidAccountError:
                # Other invalid status: this shouldn't happen unless the user happens to be in a
                # temporary state. Such state requires more updates before the user can be saved
                # to the database. (e.g. `get_or_create_user()` creates a temporary-state user.)
                message = 'Institution SSO Error: SSO is not eligible for an inactive account [{}] ' \
                          'with an unknown or invalid status'.format(username)
                sentry.log_message(message)
                logger.error(message)
                raise PermissionDenied(detail='InstitutionSsoInvalidAccount')
        else:
            logger.info('Institution SSO: new user [{}]'.format(username))

        # The `department` field is updated each login when it was changed.
        user_guid = user.guids.first()._id
        if department:
            if user.department != department:
                user.department = department
                user.save()
            logger.info('Institution SSO: user w/ dept: user=[{}], email=[{}], inst=[{}], '
                        'dept=[{}]'.format(user_guid, username, institution._id, department))
        else:
            logger.info('Institution SSO: user w/o dept: user=[{}], email=[{}], '
                        'inst=[{}]'.format(user_guid, username, institution._id))

        # Both created and activated accounts need to be updated and registered
        if created or activation_required:

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
            user.register(username, password=password)
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

        # Affiliate the user to the primary institution if not previously affiliated
        if not user.is_affiliated_with_institution(institution):
            user.affiliated_institutions.add(institution)
            user.save()

        # Affiliate the user to the secondary institution if not previously affiliated
        if secondary_institution and not user.is_affiliated_with_institution(secondary_institution):
            user.affiliated_institutions.add(secondary_institution)
            user.save()

        return user, None
