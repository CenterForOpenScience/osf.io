import json

import jwe
import jwt
import waffle

#from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from api.base import settings

from framework import sentry
from framework.auth import get_or_create_user
from framework.auth.core import get_user

from osf.models import Institution
from website.mails import send_mail, WELCOME_OSF4I
from website.settings import OSF_SUPPORT_EMAIL, DOMAIN
from website.util.quota import update_default_storage

import logging
logger = logging.getLogger(__name__)

class InstitutionAuthentication(BaseAuthentication):

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
                    "fullname":     "",
                    "familyName":   "",
                    "givenName":    "",
                    "middleNames":  "",
                    "suffix":       "",
                    "groups":       "",
                    "eptid":        "",
                }
            }
        }

        :param request: the POST request
        :return: user, None if authentication succeed
        :raises: AuthenticationFailed if authentication fails
        """

        try:
            payload = jwt.decode(
                jwe.decrypt(request.body, settings.JWE_SECRET),
                settings.JWT_SECRET,
                options={'verify_exp': False},
                algorithm='HS256',
            )
        except (jwt.InvalidTokenError, TypeError):
            raise AuthenticationFailed

        data = json.loads(payload['data'])
        provider = data['provider']

        institution = Institution.load(provider['id'])
        if not institution:
            raise AuthenticationFailed('Invalid institution id specified "{}"'.format(provider['id']))

        eppn = None
        eppn_tmp = None
        USE_EPPN = login_by_eppn()
        if USE_EPPN:
            eppn = provider['user'].get('username')
            if not eppn:
                message = 'login failed: eppn required'
                sentry.log_message(message)
                raise AuthenticationFailed(message)
            eppn_tmp = ('tmp_eppn_' + eppn).lower()
        logger.info('---InstitutionAuthentication.authenticate.user:{}'.format(provider))

        username = provider['user'].get('username')
        fullname = provider['user'].get('fullname')
        given_name = provider['user'].get('givenName')
        family_name = provider['user'].get('familyName')
        middle_names = provider['user'].get('middleNames')
        suffix = provider['user'].get('suffix')
        entitlement = provider['user'].get('entitlement')

        # use given name and family name to build full name if not provided
        if given_name and family_name and not fullname:
            fullname = given_name + ' ' + family_name

        if USE_EPPN and not fullname:
            fullname = 'New User (no name)'

        # institution must provide `fullname`, otherwise we fail the authentication and inform sentry
        if not fullname:
            message = 'Institution login failed: fullname required' \
                      ' for user {} from institution {}'.format(username, provider['id'])
            sentry.log_message(message)
            raise AuthenticationFailed(message)

        user = None
        created = False
        if USE_EPPN:
            # use user.eppn because user.username is not always ePPN.
            user = get_user(eppn=eppn)
            if user:
                created = False
            else:
                user, created = get_or_create_user(fullname, eppn_tmp, reset_password=False)
        else:
            user, created = get_or_create_user(fullname, username, reset_password=False)
        # `get_or_create_user()` guesses names from fullname
        # replace the guessed ones if the names are provided from the authentication

        if created:
            if given_name:
                user.given_name = given_name
            if family_name:
                user.family_name = family_name
            if middle_names:
                user.middle_names = middle_names
            if suffix:
                user.suffix = suffix
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
                user.have_email = False
                #user.unclaimed_records = {}
                username = eppn_tmp
            else:
                user.eppn = None
                user.have_email = True
                ### username is email address

            # save and register user
            user.save()
            user.register(username)

            # send confirmation email
            if user.have_email:
                send_mail(
                    to_addr=user.username,
                    mail=WELCOME_OSF4I,
                    mimetype='html',
                    user=user,
                    domain=DOMAIN,
                    osf_support_email=OSF_SUPPORT_EMAIL,
                    storage_flag_is_active=waffle.flag_is_active(request, 'storage_i18n'),
                )
            ### the user is not available when have_email is False.

        # update every login.
        if USE_EPPN:
            for other in user.affiliated_institutions.exclude(id=institution.id):
                user.affiliated_institutions.remove(other)
        if not user.is_affiliated_with_institution(institution):
            user.affiliated_institutions.add(institution)
            user.save()
            update_default_storage(user)

        # update every login.
        init_cloud_gateway_groups(user, provider)

        return user, None

def login_by_eppn():
    if not hasattr(settings, 'LOGIN_BY_EPPN'):
        return False
    if settings.LOGIN_BY_EPPN:
        return True
    else:
        return False

def init_cloud_gateway_groups(user, provider):
    if not hasattr(settings, 'CLOUD_GATAWAY_ISMEMBEROF_PREFIX'):
        return
    prefix = settings.CLOUD_GATAWAY_ISMEMBEROF_PREFIX
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
