# -*- coding: utf-8 -*-
"""Various text used throughout the website, e.g. status messages, errors, etc.
"""


# Status Messages
#################

# NOTE: in status messages, newlines are not preserved, so triple-quotes strings
# are ok

# Status message shown at settings page on first login
# (upon clicking primary email confirmation link)
WELCOME_MESSAGE = '''
Welcome to the OSF!
Please update the following settings. If you need assistance
in getting started, please visit the <a href="/getting-started/">Getting Started</a>
page.
'''

REGISTRATION_SUCCESS = '''
Registration successful. Please check {email} to confirm your email address.'
'''

# Shown if registration is turned off in website.settings
REGISTRATION_UNAVAILABLE = 'Registration currently unavailable.'

ALREADY_REGISTERED = '''
The email <em>{email}</em> has already been registered.
'''

# Shown if user tries to login with an email that is not yet confirmed
UNCONFIRMED = '''
This login email has been registered but not confirmed. Please check your email (and spam
folder). <a href="/resend/">Click here</a> to resend your confirmation email.
'''

# Shown on incorrect password attempt
LOGIN_FAILED = '''
Log-in failed. Please try again or reset your password.
'''

# Shown at login page if user tries to access a resource that requires auth
MUST_LOGIN = '''
You must log in to access this resource.
'''

# Shown on logout
LOGOUT = '''
You have successfully logged out.
'''

EMAIL_NOT_FOUND = '''
<strong>{email}</strong> was not found in our records.
'''


# Error Pages
# ###########

# Shown at error page if an expired/revokes email confirmation link is clicked
LINK_EXPIRED ='This confirmation link has expired. Please <a href="/login/">log in</a> to continue.'
