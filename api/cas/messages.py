# login exception messages
# must match io.cos.cas.api.util.AbstractApiEndpointUtils in CAS
ACCOUNT_NOT_FOUND = 'ACCOUNT_NOT_FOUND'
ACCOUNT_NOT_VERIFIED = 'ACCOUNT_NOT_VERIFIED'
ACCOUNT_DISABLED = 'ACCOUNT_DISABLED'
INVALID_PASSWORD = 'INVALID_PASSWORD'
INVALID_KEY = 'INVALID_VERIFICATION_KEY'
INVALID_TOTP = 'INVALID_TIME_BASED_ONE_TIME_PASSWORD'
INVALID_ACCOUNT_STATUS = 'INVALID_ACCOUNT_STATUS'
TFA_REQUIRED = 'TWO_FACTOR_AUTHENTICATION_REQUIRED'


# oauth exception messages
SCOPE_NOT_FOUND = 'Scope not found.'
SCOPE_NOT_ACTIVE = 'Scope not active.'
TOKEN_NOT_FOUND = 'PAT not found.'
TOKEN_OWNER_NOT_FOUND = 'PAT owner not found.'


# general server or client side exception messages
INVALID_REQUEST = 'The server cannot understand the request.'
REQUEST_FAILED = 'The server understands the request but fails to handle it.'


# external messages: messages that will be displayed to user on CAS page
ALREADY_REGISTERED = 'This email has already been registered.'
EMAIL_NOT_FOUND = 'Email not found.'
INVALID_CODE = 'Invalid verification code.'
RESEND_VERIFICATION_THROTTLE_ACTIVE =\
    'You have recently requested to resend your verification email. Please wait a few minutes before trying again.'
EMAIL_ALREADY_VERIFIED = 'Email already verified.'
RESET_PASSWORD_THROTTLE_ACTIVE =\
    'You have recently requested to reset your password. Please wait a few minutes before trying again.'
RESET_PASSWORD_NOT_ELIGIBLE =\
    'You cannot reset password on this account. Please contact OSF Support.'
