from framework.auth.core import User

from website.tokens.exceptions import UnsupportedSanctionHandlerKind


def sanction_handler(kind, action, payload, encoded_token):
    from website.models import RegistrationApproval, Embargo, Retraction

    Model = None

    if kind == 'registration':
        Model = RegistrationApproval
    elif kind == 'embargo':
        Model = Embargo
    elif kind == 'retraction':
        Model = Retraction
    else:
        raise UnsupportedSanctionHandlerKind

    # TODO(hrybacki): handle exceptions
    user_id = payload.get('user_id', None)
    user = User.load(user_id)
    sanction_id = payload.get('sanction_id', None)

    sanction = Model.load(sanction_id)

    action = getattr(sanction, action, None)
    if action:
        action(user, encoded_token)
