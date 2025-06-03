from django.contrib.sessions.backends.base import UpdateError
from flask import redirect, request
import markupsafe
from transitions import MachineError

from framework.auth.decorators import must_be_logged_in
from rest_framework import status as http_status

from framework.exceptions import HTTPError, PermissionsError
from framework import status

from osf.exceptions import TokenError, UnsupportedSanctionHandlerKind


from website.language import SANCTION_STATUS_MESSAGES

@must_be_logged_in
def sanction_handler_flask(kind, action, payload, encoded_token, **kwargs):
    sanction_handler(kind, action, payload, encoded_token, user=kwargs['auth'].user)

def sanction_handler(kind, action, payload, encoded_token, user):
    from osf.models import (
        RegistrationApproval,
        Embargo,
        EmbargoTerminationApproval,
        Retraction
    )
    match kind:
        case 'registration':
            Sanction = RegistrationApproval
        case 'embargo':
            Sanction = Embargo
        case 'embargo_termination_approval':
            Sanction = EmbargoTerminationApproval
        case 'retraction':
            Sanction = Retraction
        case _:
            raise UnsupportedSanctionHandlerKind

    sanction_id = payload.get('sanction_id')
    sanction = Sanction.load(sanction_id)
    if not sanction:
        raise HTTPError(
            http_status.HTTP_400_BAD_REQUEST,
            data={'message_long': f'There is no {markupsafe.escape(Sanction.DISPLAY_NAME)} associated with this token.'}
        )

    if sanction.is_approved:
        return redirect(request.base_url)

    if sanction.is_rejected:
        raise HTTPError(
            http_status.HTTP_410_GONE if kind in ('registration', 'embargo') else http_status.HTTP_400_BAD_REQUEST,
            data={'message_long': f'This registration {markupsafe.escape(sanction.DISPLAY_NAME)} has been rejected.'}
        )

    do_action = getattr(sanction, action, None)
    if not do_action:
        raise HTTPError(
            http_status.HTTP_400_BAD_REQUEST,
            data={'message_long': f'Invalid action "{action}" for sanction type "{kind}".'}
        )

    try:
        do_action(user=user, token=encoded_token)
    except TokenError as e:
        raise HTTPError(
            http_status.HTTP_400_BAD_REQUEST,
            data={'message_short': getattr(e, 'message_short', 'Token error'), 'message_long': str(e)}
        )
    except PermissionsError as e:
        raise HTTPError(
            http_status.HTTP_403_FORBIDDEN,
            data={'message_short': 'Unauthorized access', 'message_long': str(e)}
        )
    except MachineError as e:
        raise HTTPError(
            http_status.HTTP_400_BAD_REQUEST,
            data={'message_short': 'Operation not allowed at this time', 'message_long': getattr(e, 'value', str(e))}
        )

    sanction.save()

    try:
        message = SANCTION_STATUS_MESSAGES.get(kind, {}).get(action)
        if message:
            status.push_status_message(message, kind='success', trust=False)
    except UpdateError:  # outside of message context in Django
        pass
