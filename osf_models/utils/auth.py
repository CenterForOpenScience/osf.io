from modularodm.exceptions import QueryException
from modularodm import Q

from framework.sessions import session

def _get_current_user():
    # avoid cirdep
    from osf_models.models import OSFUser
    uid = session._get_current_object() and session.data.get('auth_user_id')
    return OSFUser.objects.get(_guid__guid=uid)


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
            from osf_models.models import PrivateLink

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
