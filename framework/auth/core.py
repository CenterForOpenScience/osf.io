# -*- coding: utf-8 -*-

import datetime as dt

import logging

from django.utils import timezone
from django.core.validators import URLValidator
from flask import request
from framework.sessions import session

from osf.exceptions import ValidationValueError, ValidationError
from osf.utils.requests import check_select_for_update
from website import security, settings

name_formatters = {
    'long': lambda user: user.fullname,
    'surname': lambda user: user.family_name if user.family_name else user.fullname,
    'initials': lambda user: u'{surname}, {initial}.'.format(
        surname=user.family_name,
        initial=user.given_name_initial,
    ),
}

logger = logging.getLogger(__name__)


def generate_verification_key(verification_type=None):
    """
    Generate a one-time verification key with an optional expiration time.
    The type of the verification key determines the expiration time defined in `website.settings.EXPIRATION_TIME_DICT`.

    :param verification_type: None, verify, confirm or claim
    :return: a string or a dictionary
    """
    token = security.random_string(30)
    # v1 with only the token
    if not verification_type:
        return token
    # v2 with a token and the expiration time
    expires = timezone.now() + dt.timedelta(minutes=settings.EXPIRATION_TIME_DICT[verification_type])
    return {
        'token': token,
        'expires': expires,
    }


def validate_year(item):
    if item:
        try:
            int(item)
        except ValueError:
            raise ValidationValueError('Please enter a valid year.')
        else:
            if len(item) != 4:
                raise ValidationValueError('Please enter a valid year.')

validate_url = URLValidator()


def validate_profile_websites(profile_websites):
    for value in profile_websites or []:
        try:
            validate_url(value)
        except ValidationError:
            # Reraise with a better message
            raise ValidationError('Invalid personal URL.')


def validate_social(value):
    validate_profile_websites(value.get('profileWebsites'))


def get_current_user_id():
    return session._get_current_object() and session.data.get('auth_user_id')

# TODO - rename to _get_current_user_from_session /HRYBACKI
def _get_current_user():
    from osf.models import OSFUser
    current_user_id = get_current_user_id()
    if current_user_id:
        return OSFUser.load(current_user_id, select_for_update=check_select_for_update(request))
    else:
        return None

def get_user_query_by_email(email):
    from osf.models import OSFUser
    from django.contrib.contenttypes.models import ContentType
    return OSFUser.objects.raw('''
        SELECT *,
            (SELECT JSON_AGG(JSON_BUILD_ARRAY(osf_guid.modified, osf_guid.id, osf_guid._id, osf_guid.content_type_id, osf_guid.object_id, osf_guid.created)
                ORDER BY osf_guid.created DESC) AS __fields
            FROM osf_guid
            WHERE (osf_guid.object_id = osf_osfuser.id)
                AND (osf_guid.content_type_id = %s)) AS __guids
        FROM osf_osfuser
        WHERE (osf_osfuser.username = %s
            OR osf_osfuser.id =
            (SELECT osf_email.user_id
            FROM osf_email
            WHERE osf_email.address = %s));
        ''', [ContentType.objects.get_for_model(OSFUser).id, email, email])

def get_user_query_by_token(token):
    from osf.models import OSFUser
    from django.contrib.contenttypes.models import ContentType
    return OSFUser.objects.raw('''
        SELECT *,
            (SELECT JSON_AGG(JSON_BUILD_ARRAY(U0.modified, U0.id, U0._id, U0.content_type_id, U0.object_id, U0.created)
                ORDER BY U0.created DESC) AS __fields
            FROM osf_guid U0
            WHERE (U0.object_id = osf_osfuser.id)
                AND (U0.content_type_id = %s)) AS __guids
        FROM osf_osfuser
        WHERE osf_osfuser.verification_key = %s
        ''', [ContentType.objects.get_for_model(OSFUser).id, token])

def get_user_query_by_external_provider(external_id_provider, external_id):
    from osf.models import OSFUser
    from django.contrib.contenttypes.models import ContentType
    return OSFUser.objects.raw('''
        SELECT *,

          (SELECT JSON_AGG(JSON_BUILD_ARRAY(U0.modified, U0.id, U0._id, U0.content_type_id, U0.object_id, U0.created)
                           ORDER BY U0.created DESC) AS __fields
           FROM osf_guid U0
           WHERE (U0.object_id = osf_osfuser.id)
             AND (U0.content_type_id = %s)) AS __guids
        FROM osf_osfuser
        WHERE (osf_osfuser.external_identity #> ARRAY[%s,
                                                          %s]) = '"VERIFIED"'
        ''', [ContentType.objects.get_for_model(OSFUser).id, external_id_provider, external_id])

# TODO: This should be a class method of User?
def get_user(email=None, password=None, token=None, external_id_provider=None, external_id=None):
    """
    Get an instance of `User` matching the provided params.

    1. email
    2. email and password
    3  token
    4. external_id_provider and external_id

    :param token: the token in verification key
    :param email: user's email
    :param password: user's password
    :param external_id_provider: the external identity provider
    :param external_id: the external id
    :rtype User or None
    """
    if not any([email, password, token, external_id_provider, external_id_provider]):
        return None

    if password and not email:
        raise AssertionError('If a password is provided, an email must also be provided.')

    if email:
        email = email.strip().lower()
        user_query = get_user_query_by_email(email)

    if token:
        user_query = get_user_query_by_token(token)

    if external_id_provider and external_id:
        user_query = get_user_query_by_external_provider(external_id_provider, external_id)

    try:
        user = user_query[0]
        if password:
            password = password.strip()
            if user and not user.check_password(password):
                return False
        return user
    except Exception as err:
        logger.error(err)
        return None

class Auth(object):

    def __init__(self, user=None, api_node=None,
                 private_key=None):
        self.user = user
        self.api_node = api_node
        self.private_key = private_key

    def __repr__(self):
        return ('<Auth(user="{self.user}", '
                'private_key={self.private_key})>').format(self=self)

    @property
    def logged_in(self):
        return self.user is not None

    @property
    def private_link(self):
        if not self.private_key:
            return None
        # Avoid circular import
        from osf.models import PrivateLink
        try:
            private_link = PrivateLink.objects.get(key=self.private_key)

            if private_link.is_deleted:
                return None

        except PrivateLink.DoesNotExist:
            return None

        return private_link

    @classmethod
    def from_kwargs(cls, request_args, kwargs):
        user = request_args.get('user') or kwargs.get('user') or _get_current_user()
        private_key = request_args.get('view_only')
        return cls(
            user=user,
            private_key=private_key,
        )
