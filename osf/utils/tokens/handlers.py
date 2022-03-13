from rest_framework import status as http_status

from flask import redirect, request
import markupsafe

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError, PermissionsError
from framework import status
from transitions import MachineError

from osf.exceptions import UnsupportedSanctionHandlerKind, TokenError

def registration_approval_handler(action, registration, registered_from):
    status.push_status_message(
        message={
            'approve': 'Your registration approval has been accepted.',
            'reject': 'Your disapproval has been accepted and the registration has been cancelled.',
        }[action],
        id={
            'approve': 'registration_approved',
            'reject': 'registration_rejected'
        }[action],
        kind='success',
        trust=False
    )
    # Allow decorated view function to return response
    return None

def embargo_handler(action, registration, registered_from):
    status.push_status_message(
        message={
            'approve': 'Your embargo approval has been accepted.',
            'reject': 'Your disapproval has been accepted and the embargo has been cancelled.',
        }[action],
        id={
            'approve': 'embargo_approved',
            'reject': 'embargo_rejected'
        }[action],
        kind='success',
        trust=False
    )
    # Allow decorated view function to return response
    return None

def embargo_termination_handler(action, registration, registered_from):
    status.push_status_message(
        message={
            'approve': 'Your approval to make this embargo public has been accepted.',
            'reject': 'Your disapproval has been accepted and this embargo will not be made public.',
        }[action],
        id={
            'approve': 'embargo_termination_approved',
            'reject': 'embargo_termination_rejected'
        }[action],
        kind='success',
        trust=False
    )
    # Allow decorated view function to return response
    return None

def retraction_handler(action, registration, registered_from):
    status.push_status_message(
        message={
            'approve': 'Your withdrawal approval has been accepted.',
            'reject': 'Your disapproval has been accepted and the withdrawal has been cancelled.'
        }[action],
        id={
            'approve': 'retraction_approved',
            'reject': 'retraction_rejected'
        }[action],
        kind='success',
        trust=False
    )
    # Allow decorated view function to return response
    return None

@must_be_logged_in
def sanction_handler(kind, action, payload, encoded_token, auth, **kwargs):
    from osf.models import (
        Embargo,
        EmbargoTerminationApproval,
        RegistrationApproval,
        Retraction
    )

    Model = {
        'registration': RegistrationApproval,
        'embargo': Embargo,
        'embargo_termination_approval': EmbargoTerminationApproval,
        'retraction': Retraction
    }.get(kind, None)
    if not Model:
        raise UnsupportedSanctionHandlerKind

    sanction_id = payload.get('sanction_id', None)
    sanction = Model.load(sanction_id)

    err_code = None
    err_message = None
    if not sanction:
        err_code = http_status.HTTP_400_BAD_REQUEST
        err_message = 'There is no {0} associated with this token.'.format(
            markupsafe.escape(Model.DISPLAY_NAME))
    elif sanction.is_approved:
        # Simply strip query params and redirect if already approved
        return redirect(request.base_url)
    elif sanction.is_rejected:
        err_code = http_status.HTTP_410_GONE if kind in ['registration', 'embargo'] else http_status.HTTP_400_BAD_REQUEST
        err_message = 'This registration {0} has been rejected.'.format(
            markupsafe.escape(sanction.DISPLAY_NAME))
    if err_code:
        raise HTTPError(err_code, data=dict(
            message_long=err_message
        ))

    do_action = getattr(sanction, action, None)
    if do_action:
        registration = sanction.registrations.get()
        registered_from = registration.registered_from
        try:
            do_action(user=auth.user, token=encoded_token)
        except TokenError as e:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': e.message_short,
                'message_long': str(e)
            })
        except PermissionsError as e:
            raise HTTPError(http_status.HTTP_401_UNAUTHORIZED, data={
                'message_short': 'Unauthorized access',
                'message_long': str(e)
            })
        except MachineError as e:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': 'Operation not allowed at this time',
                'message_long': e.value
            })
        sanction.save()
        return {
            'registration': registration_approval_handler,
            'embargo': embargo_handler,
            'embargo_termination_approval': embargo_termination_handler,
            'retraction': retraction_handler,
        }[kind](action, registration, registered_from)
