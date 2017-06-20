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

ACCOUNT_NOT_ELIGIBLE =\
    'The OSF account associated with this email is not eligible for the requested action. Please contact OSF support.'

EMAIL_THROTTLE_ACTIVE =\
    'You have recently make the same request. Please wait a few minutes before trying again.'
