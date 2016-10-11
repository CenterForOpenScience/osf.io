import logging

from django.apps import apps
from modularodm.exceptions import QueryException
from modularodm import Q

from framework.sessions import session

logger = logging.getLogger(__name__)

def _get_current_user():
    # avoid cirdep
    from osf.models import OSFUser
    uid = session._get_current_object() and session.data.get('auth_user_id')
    return OSFUser.load(uid)

# TODO: This should be a class method of User?
def get_user(email=None, password=None, verification_key=None):
    """Get an instance of User matching the provided params.

    :return: The instance of User requested
    :rtype: User or None
    """
    User = apps.get_model('osf.OSFUser')
    # tag: database
    if password and not email:
        raise AssertionError('If a password is provided, an email must also '
                             'be provided.')

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
            user = User.find_one(query)
        except Exception as err:
            logger.error(err)
            user = None
        if user and not user.check_password(password):
            return False
        return user
    if verification_key:
        query_list.append(Q('verification_key', 'eq', verification_key))
    try:
        query = query_list[0]
        for query_part in query_list[1:]:
            query = query & query_part
        user = User.find_one(query)
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
            from osf.models import PrivateLink

            private_link = PrivateLink.objects.get(key=self.private_key)

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
