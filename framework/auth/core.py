# -*- coding: utf-8 -*-

import datetime as dt

import itertools
import logging

from django.utils import timezone
from framework.mongo.validators import string_required
from framework.sessions import session
from modularodm import Q
from modularodm.exceptions import QueryException, ValidationError, ValidationValueError
from modularodm.validators import URLValidator
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


def validate_history_item(item):
    string_required(item.get('institution'))
    startMonth = item.get('startMonth')
    startYear = item.get('startYear')
    endMonth = item.get('endMonth')
    endYear = item.get('endYear')

    validate_year(startYear)
    validate_year(endYear)

    if startYear and endYear:
        if endYear < startYear:
            raise ValidationValueError('End date must be later than start date.')
        elif endYear == startYear:
            if endMonth and startMonth and endMonth < startMonth:
                raise ValidationValueError('End date must be later than start date.')


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
        return OSFUser.load(current_user_id)
    else:
        return None


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
    from osf.models import OSFUser

    if password and not email:
        raise AssertionError('If a password is provided, an email must also be provided.')

    query_list = []

    if email:
        email = email.strip().lower()
        query_list.append(Q('emails', 'eq', email) | Q('username', 'eq', email))

    if password:
        password = password.strip()
        try:
            query = query_list[0]
            for query_part in query_list[1:]:
                query = query & query_part
            user = OSFUser.find_one(query)
        except Exception as err:
            logger.error(err)
            user = None
        if user and not user.check_password(password):
            return False
        return user

    if token:
        query_list.append(Q('verification_key', 'eq', token))

    if external_id_provider and external_id:
        query_list.append(Q('external_identity.{}.{}'.format(external_id_provider, external_id), 'eq', 'VERIFIED'))

    try:
        query = query_list[0]
        for query_part in query_list[1:]:
            query = query & query_part
        user = OSFUser.find_one(query)
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
        try:
            # Avoid circular import
            from website.project.model import PrivateLink
            private_link = PrivateLink.find_one(
                Q('key', 'eq', self.private_key)
            )

            if private_link.is_deleted:
                return None

        except QueryException:
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


def _merge_into_reversed(*iterables):
    '''Merge multiple sorted inputs into a single output in reverse order.
    '''
    return sorted(itertools.chain(*iterables), reverse=True)
