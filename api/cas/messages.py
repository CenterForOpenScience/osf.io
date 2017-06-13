# Error messages that will be used in log or displayed to the user on the page.

# cas log: oauth exception messages

SCOPE_NOT_FOUND = 'The scope is not found.'

SCOPE_NOT_ACTIVE = 'The scope is not active.'

TOKEN_NOT_FOUND = 'The personal access token is not found.'

TOKEN_OWNER_NOT_FOUND = 'The personal access token\'s owner is not found.'

# cas log: general server (API) or client (CAS) side exception messages

INVALID_REQUEST =\
    'The API server fails to understand the CAS request. Please check if CAS or API endpoints have changed.'

REQUEST_FAILED =\
    'The API server fails to complete the CAS request. Please check if CAS or related API CAS endpoint have changed.'

# cas account messages that will be shown to the user on CAS pages

ALREADY_REGISTERED = 'This email has already been registered.'

EMAIL_NOT_FOUND = 'The email is not found.'

INVALID_CODE = 'The verification code is invalid.'

ALREADY_VERIFIED = 'This email has already been verified.'

RESET_PASSWORD_NOT_ELIGIBLE =\
    'You cannot reset password on this account. Please contact OSF support.'

EXTERNAL_IDENTITY_NOT_ELIGIBLE = 'The OSF account associated with this email is not eligible. Please contact OSF support.'

RESEND_VERIFICATION_THROTTLE_ACTIVE =\
    'You have recently requested to resend your verification email. Please wait a few minutes before trying again.'

RESET_PASSWORD_THROTTLE_ACTIVE =\
    'You have recently requested to reset your password. Please wait a few minutes before trying again.'
