import json
import uuid
import logging

import jwe
import jwt
import waffle

#from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from api.base.authentication import drf
from api.base import exceptions, settings

from framework import sentry
from framework.auth import get_or_create_user
from framework.auth.core import get_user

from osf import features
from osf.models import Institution, UserExtendedData
from osf.exceptions import BlacklistedEmailError
from website.mails import send_mail, WELCOME_OSF4I
from website.settings import OSF_SUPPORT_EMAIL, DOMAIN, to_bool
from website.util.quota import update_default_storage

logger = logging.getLogger(__name__)


import logging
logger = logging.getLogger(__name__)

NEW_USER_NO_NAME = 'New User (no name)'

def send_welcome(user, request):
    send_mail(
        to_addr=user.username,
        mail=WELCOME_OSF4I,
        mimetype='html',
        user=user,
        domain=DOMAIN,
        osf_support_email=OSF_SUPPORT_EMAIL,
        storage_flag_is_active=waffle.flag_is_active(
            request,
            features.STORAGE_I18N,
        ),
        use_viewonlylinks=to_bool('USE_VIEWONLYLINKS', True),
    )

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
                "idp":  "",
                "id":   "",
                "user": {
                    "username":     "",  # email or eppn
                    "fullname":     "",  # displayName
                    "familyName":   "",  # sn or surname
                    "givenName":    "",
                    "middleNames":  "",
                    "jaDisplayName": "",
                    "jaSurname":     "",  # jasn
                    "jaGivenName":   "",
                    "jaMiddleNames": "",
                    "suffix":       "",
                    "groups":       "",  # isMemberOf for mAP API v1
                    "eptid":        "",  # persistent-id for mAP API v1
                    "entitlement":  "",  # eduPersonEntitlement
                    "email":        "",  # mail
                    "organizationName": "",    # o
                    "organizationalUnit": "",  # ou
                    "jaOrganizationName": "",  # jao
                    "jaOrganizationalUnitName": "",  # jaou
                }
            }
        }

        :param request: the POST request
        :return: user, None if authentication succeed
        :raises: AuthenticationFailed if authentication fails
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
            raise AuthenticationFailed

        # Load institution and user data
        data = json.loads(payload['data'])
        provider = data['provider']
        institution = Institution.load(provider['id'])
        if not institution:
            raise AuthenticationFailed('Invalid institution id: "{}"'.format(provider['id']))

        USE_EPPN = login_by_eppn()

        logger.info('---InstitutionAuthentication.authenticate.user:{}'.format(provider))

        p_idp = provider['idp']
        p_user = provider['user']

        def get_next(obj, *args):
            ret = None
            for key in args:
                val = obj.get(key)
                if val is not None:
                    ret = val
                if val:
                    break
            return ret

        # username
        username = p_user.get('username')
        # display name: 'displayName' is friendlyName
        fullname = get_next(p_user, 'displayName', 'fullname')
        # first name: 'givenName' is friendlyName
        given_name = get_next(p_user, 'givenName', 'firstName')
        # last name: 'sn' is friendlyName
        family_name = get_next(p_user, 'sn', 'surname', 'familyName', 'lastName')
        # middle names
        middle_names = p_user.get('middleNames')
        # suffix name
        suffix = p_user.get('suffix')
        # display name: 'jaDisplayName' is friendlyName
        fullname_ja = get_next(p_user, 'jaDisplayName', 'jaFullname')
        # first name: 'jaGivenName' is friendlyName
        given_name_ja = get_next(p_user, 'jaGivenName', 'jaFirstName')
        # last name: 'jasn' is friendlyName
        family_name_ja = get_next(p_user, 'jasn', 'jaSurname', 'jaFamilyName', 'jaLastName')
        # middle names
        middle_names_ja = p_user.get('jaMiddleNames')
        # department
        department = p_user.get('department')
        # entitlement: 'eduPersonEntitlement' is friendlyName
        entitlement = get_next(p_user, 'eduPersonEntitlement', 'entitlement')
        # email: 'mail' is friendlyName
        mail = email = get_next(p_user, 'mail', 'email')
        # organization: 'o' is friendlyName
        organization_name = get_next(p_user, 'o', 'organizationName')
        # affiliation: 'ou' is friendlyName
        organizational_unit = get_next(p_user, 'ou', 'organizationalUnitName')
        # organization: 'jao' is friendlyName
        organization_name_ja = get_next(p_user, 'jao', 'jaOrganizationName')
        # affiliation: 'jaou' is friendlyName
        organizational_unit_ja = get_next(p_user, 'jaou', 'jaOrganizationalUnitName')

        # Use given name and family name to build full name if it is not provided
        if given_name and family_name and not fullname:
            fullname = given_name + ' ' + family_name
        if given_name_ja and family_name_ja and not fullname_ja:
            fullname_ja = given_name_ja + ' ' + family_name_ja

        if USE_EPPN and not fullname:
            fullname = NEW_USER_NO_NAME

        # Non-empty full name is required. Fail the auth and inform sentry if not provided.
        if not fullname:
            message = 'Institution login failed: fullname required for ' \
                      'user "{}" from institution "{}"'.format(username, provider['id'])
            sentry.log_message(message)
            raise AuthenticationFailed(message)

        user = None
        created = False
        eppn = None

        if USE_EPPN:
            eppn = username
            if not eppn:
                message = 'Institution login failed: eppn required'
                sentry.log_message(message)
                raise AuthenticationFailed(message)

            # use user.eppn as primary-key in GakuNin RDM
            user = get_user(eppn=eppn, log=False)
            if user:
                created = False
            else:  # new user
                if email:
                    existing_user = get_user(email=email, log=False)
                    if existing_user and \
                       existing_user.eppn != eppn:  # suppose race-condition
                        email = None  # require other email address
                tmp_eppn = ('tmp_eppn_' + eppn).lower()
                if email:
                    username_tmp = email
                else:
                    username_tmp = tmp_eppn
                try:
                    # try to use email or tmp_eppn
                    user, created = get_or_create_user(
                        fullname, username_tmp,
                        reset_password=False,
                    )
                except BlacklistedEmailError:
                    if username_tmp == tmp_eppn:  # unexpected
                        raise
                    # email is Black Listed Email
                    email = None
                    # try to use tmp_eppn only
                    user, created = get_or_create_user(
                        fullname, tmp_eppn,
                        reset_password=False,
                    )
        else:
            user, created = get_or_create_user(fullname, username, reset_password=False)
        # Get an existing user or create a new one. If a new user is created, the user object is
        # confirmed but not registered,which is temporarily of an inactive status. If an existing
        # user is found, it is also possible that the user is inactive (e.g. unclaimed, disabled,
        # unconfirmed, etc.).

        # Existing but inactive users need to be either "activated" or failed the auth
        activation_required = False
        new_password_required = False
        if not created:
            try:
                drf.check_user(user)
                logger.info('Institution SSO: active user "{}"'.format(username))
            except exceptions.UnclaimedAccountError:
                # Unclaimed user (i.e. a user that has been added as an unregistered contributor)
                user.unclaimed_records = {}
                activation_required = True
                # Unclaimed users have an unusable password when being added as an unregistered
                # contributor. Thus a random usable password must be assigned during activation.
                new_password_required = True
                logger.info('Institution SSO: unclaimed contributor "{}"'.format(username))
            except exceptions.UnconfirmedAccountError:
                if user.has_usable_password():
                    # Unconfirmed user from default username / password signup
                    user.email_verifications = {}
                    activation_required = True
                    # Unconfirmed users already have a usable password set by the creator during
                    # sign-up. However, it must be overwritten by a new random one so the creator
                    # (if he is not the real person) can not access the account after activation.
                    new_password_required = True
                    logger.info('Institution SSO: unconfirmed user "{}"'.format(username))
                else:
                    # Login take-over has not been implemented for unconfirmed user created via
                    # external IdP login (ORCiD).
                    message = 'Institution SSO is not eligible for an unconfirmed account ' \
                              'created via external IdP login: username = "{}"'.format(username)
                    sentry.log_message(message)
                    logger.error(message)
                    return None, None
            except exceptions.DeactivatedAccountError:
                # Deactivated user: login is not allowed for deactivated users
                message = 'Institution SSO is not eligible for a deactivated account: ' \
                          'username = "{}"'.format(username)
                sentry.log_message(message)
                logger.error(message)
                return None, None
            except exceptions.MergedAccountError:
                # Merged user: this shouldn't happen since merged users do not have an email
                message = 'Institution SSO is not eligible for a merged account: ' \
                          'username = "{}"'.format(username)
                sentry.log_message(message)
                logger.error(message)
                return None, None
            except exceptions.InvalidAccountError:
                # Other invalid status: this shouldn't happen unless the user happens to be in a
                # temporary state. Such state requires more updates before the user can be saved
                # to the database. (e.g. `get_or_create_user()` creates a temporary-state user.)
                message = 'Institution SSO is not eligible for an inactive account with ' \
                          'an unknown or invalid status: username = "{}"'.format(username)
                sentry.log_message(message)
                logger.error(message)
                return None, None
        else:
            logger.info('Institution SSO: new user "{}"'.format(username))

        # The `department` field is updated each login when it was changed.
        if department and user.department != department:
            user.department = department
            user.save()

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

            if given_name_ja:
                user.given_name_ja = given_name_ja
            if family_name_ja:
                user.family_name_ja = family_name_ja
            if middle_names_ja:
                user.middle_names_ja = middle_names_ja

            # Users claimed or confirmed via institution SSO should have their full name updated
            if activation_required:
                user.fullname = fullname

            user.update_date_last_login()

            ## Relying on front-end validation until `accepted_tos` is added to the JWT payload
            #user.accepted_terms_of_service = timezone.now()
            if settings.USER_TIMEZONE:
                user.timezone = settings.USER_TIMEZONE

            if settings.USER_LOCALE:
                user.locale = settings.USER_LOCALE

            if entitlement:
                if 'GakuninRDMAdmin' in entitlement:
                    user.is_staff = True

            if USE_EPPN:
                user.eppn = eppn
                if email:
                    username = email
                    user.have_email = True
                else:
                    username = user.username
                    user.have_email = False
                    #user.unclaimed_records = {}
                if organization_name:
                    # Settings > Profile information > Employment > ...
                    #   organization_name (o) : Institution / Employer
                    #   organizational_unit (ou) : Department / Institute
                    job = {
                        'title': '',
                        'institution': organization_name,  # required
                        'institution_ja': '',  # required
                        'department': '',
                        'department_ja': '',
                        'location': '',
                        'startMonth': '',
                        'startYear': '',
                        'endMonth': '',
                        'endYear': '',
                        'ongoing': False,
                    }
                    if organization_name_ja:
                        job['institution_ja'] = organization_name_ja
                    if organizational_unit:
                        job['department'] = organizational_unit
                    if organizational_unit_ja:
                        job['department_ja'] = organizational_unit_ja
                    user.jobs.append(job)
            else:
                user.eppn = None
                user.have_email = True
                ### username is email address

            # Register and save user
            password = str(uuid.uuid4()) if new_password_required else None
            user.register(username, password=password)
            user.save()

            # send confirmation email
            if user.have_email:
                send_welcome(user, request)
            ### the user is not available when have_email is False.

        ext, created = UserExtendedData.objects.get_or_create(user=user)
        # update every login.
        ext.set_idp_attr(
            {
                'idp': p_idp,
                'eppn': eppn,
                'username': username,
                'fullname': fullname,
                'fullname_ja': fullname_ja,
                'entitlement': entitlement,
                'email': mail,
                'organization_name': organization_name,
                'organizational_unit': organizational_unit,
                'organization_name_ja': organization_name_ja,
                'organizational_unit_ja': organizational_unit_ja,
            },
        )

        # update every login.
        if USE_EPPN:
            for other in user.affiliated_institutions.exclude(id=institution.id):
                user.affiliated_institutions.remove(other)

        # Affiliate the user if not previously affiliated
        if not user.is_affiliated_with_institution(institution):
            user.affiliated_institutions.add(institution)
            user.save()
            update_default_storage(user)

        # update every login. (for mAP API v1)
        init_cloud_gateway_groups(user, provider)

        return user, None

def login_by_eppn():
    return settings.LOGIN_BY_EPPN

def init_cloud_gateway_groups(user, provider):
    if not hasattr(settings, 'CLOUD_GATEWAY_ISMEMBEROF_PREFIX'):
        return
    prefix = settings.CLOUD_GATEWAY_ISMEMBEROF_PREFIX
    if not prefix:
        return

    eptid = provider['user'].get('eptid')
    if not eptid:
        return  # Cloud Gateway may not be alive.

    # set ePTID (eduPersonTargetedID, persistent-id)
    user.eptid = eptid

    debug = False
    #debug = True

    if debug:
        groups_str = ''
        if user.eppn == 'test002@nii.ac.jp':
            groups_str = 'https://sptest.cg.gakunin.jp/gr/group1;https://sptest.cg.gakunin.jp/gr/group1/admin;https://sptest.cg.gakunin.jp/gr/group2;https://sptest.cg.gakunin.jp/gr/group2/admin;https://sptest.cg.gakunin.jp/gr/group3'
        elif user.eppn == 'test003@nii.ac.jp':
            groups_str = 'https://sptest.cg.gakunin.jp/gr/group1;https://sptest.cg.gakunin.jp/gr/group1/admin;https://sptest.cg.gakunin.jp/gr/group2'
    else:
        groups_str = provider['user'].get('groups')
        if groups_str is None:
            groups_str = ''

    # clear groups
    user.cggroups.clear()
    user.cggroups_admin.clear()
    user.cggroups_sync.clear()
    user.cggroups_initialized = False  # for framework/auth/decorators.py

    # set groups
    import re
    patt_prefix = re.compile('^' + prefix)
    patt_admin = re.compile('(.+)/admin$')
    for group in groups_str.split(';'):
        if patt_prefix.match(group):
            groupname = patt_prefix.sub('', group)
            if groupname is None or groupname == '':
                continue
            m = patt_admin.search(groupname)
            if m:  # is admin
                user.add_group_admin(m.group(1))
            else:
                user.add_group(groupname)
    user.save()
