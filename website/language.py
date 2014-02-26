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
Registration successful. Please check {email} to confirm your email address.
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

# Node Actions

BEFORE_REGISTER_HAS_POINTERS = (
    'This {category} contains links to other projects. Links will be copied '
    'into your registration, but the projects that they link to will not be '
    'registered. If you wish to register the linked projects, they need to be '
    'registered from the original project in order to be part of this project.'
)

BEFORE_FORK_HAS_POINTERS = (
    'This {category} contains links to other projects. Links will be copied '
    'into your fork, but the projects that they link to will not be forked. '
    'If you wish to fork the linked projects, they need to be forked from the '
    'original project in order to be part of this project.'
)

REGISTRATION_INFO = '''
<p>You can register your project by selecting a registration form, then enter
information about your project, and then confirming. Registration creates a
frozen version of the project that can never be edited or deleted. You will be
able to continue editing the project, and the frozen version with time stamps
will always be linked to the project.</p>

<ul>

    <li>Registrations are private by default. You can make your registration
    public after completing the registration process.</li>

    <li>Before initiating a registration, make sure that the project is in the
    state that you wish to freeze.</li>

    <li>Start by selecting a registration form from the list below. You can
    back-up if the selected form is not appropriate for your use.</li>

</ul>
'''

BEFORE_REGISTRATION_INFO = '''
Registration cannot be undone, and the archived content and files cannot be
deleted after registration. Please be sure the project is complete and
comprehensive for what you wish to register.
'''
