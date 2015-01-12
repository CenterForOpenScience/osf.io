
# -*- coding: utf-8 -*-
"""Various text used throughout the website, e.g. status messages, errors, etc.
"""


# Status Messages
#################

# NOTE: in status messages, newlines are not preserved, so triple-quotes strings
# are ok

# Status message shown at settings page on first login
# (upon clicking primary email confirmation link)
WELCOME_MESSAGE = ('Welcome to the OSF! Please update the following settings. If you need assistance '
                   'in getting started, please visit the <a href="/getting-started/">Getting Started</a> page.')

REGISTRATION_SUCCESS = '''Registration successful. Please check {email} to confirm your email address.'''

# Shown if registration is turned off in website.settings
REGISTRATION_UNAVAILABLE = 'Registration currently unavailable.'

ALREADY_REGISTERED = '''The email {email} has already been registered.'''

# Shown if user tries to login with an email that is not yet confirmed
UNCONFIRMED = ('This login email has been registered but not confirmed. Please check your email (and spam folder).'
               ' <a href="/resend/">Click here</a> to resend your confirmation email.')

# Shown if the user's account is disabled
DISABLED = '''
Log-in failed: Deactivated account.
'''

# Shown on incorrect password attempt
LOGIN_FAILED = '''
Log-in failed. Please try again or reset your password.
'''

# Shown if incorrect 2fa verification is entered at login
TWO_FACTOR_FAILED = '''
You entered an incorrect verification code. Please try again.
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

# Shown after an unregistered user claims an account and is redirected to the
# settings page
CLAIMED_CONTRIBUTOR = ('<strong>Welcome to the OSF!</strong> Edit your display name below and then check your '
                       '<a href="/dashboard/">dashboard</a> to see projects to which you have been added as a '
                       'contributor by someone else.')

# Error Pages
# ###########

# Shown at error page if an expired/revokes email confirmation link is clicked
LINK_EXPIRED = 'This confirmation link has expired. Please <a href="/login/">log in</a> to continue.'

# Node Actions

BEFORE_REGISTER_HAS_POINTERS = (
    'This {category} contains links to other projects. Links will be copied '
    'into your registration, but the projects that they link to will not be '
    'registered. If you wish to register the linked projects, you must fork '
    'them from the original project before registering.'
)

BEFORE_FORK_HAS_POINTERS = (
    'This {category} contains links to other projects. Links will be copied '
    'into your fork, but the projects that they link to will not be forked. '
    'If you wish to fork the linked projects, they need to be forked from the '
    'original project.'
)

REGISTRATION_INFO = '''
<p>Registration creates a frozen version of the project that can never be edited
or deleted. You can register your project by selecting a registration form,  entering
information about your project, and then confirming. You will be
able to continue editing the original project, however, and the frozen version with
time stamps will always be linked to the original.</p>

<ul>

    <li>A registration takes the same privacy settings as the project, e.g. a public project results in a public registration.</li>

    <li>Before initiating a registration, make sure that the project is in the
    state that you wish to freeze. Consider turning links into forks.</li>

    <li>Start by selecting a registration form from the list below. You can
    hit your browser's back button if the selected form is not
    appropriate for your use.</li>

</ul>
'''

BEFORE_REGISTRATION_INFO = '''
Registration cannot be undone, and the archived content and files cannot be
deleted after registration. Please be sure the project is complete and
comprehensive for what you wish to register.
'''

# Nodes: forking, templating, linking

LINK_ACTION = 'Link to this Project'
LINK_DESCRIPTION = """
Linking to this project will reference it in another project, without
creating a copy. The link will always point to the most up-to-date version.
"""

TEMPLATE_ACTION = 'Copy Project Structure'
TEMPLATE_DESCRIPTION = """
This option will create a new project, using this project as a template.
The new project will be structured in the same way, but contain no data.
"""

FORK_ACTION = 'Fork this Project'
FORK_DESCRIPTION = """
Fork this project if you plan to build upon it in your own work.
The new project will be an exact duplicate of this project's current state,
with you as the only contributor.
"""

TEMPLATE_DROPDOWN_HELP = """Start typing to search. Selecting project as
template will duplicate its structure in the new project without importing the
content of that project."""

TEMPLATED_FROM_PREFIX = "Templated from "

# MFR Error handling
ERROR_PREFIX = "Unable to render. <a href='{download_path}'>Download</a> file to view it."
SUPPORT = "Contact support@osf.io for further assistance."

# Custom Error Messages w/ support
STATA_VERSION_ERROR = 'Version of given Stata file is not 104, 105, 108, 113 (Stata 8/9), 114 (Stata 10/11) or 115 (Stata 12)<p>{0}</p>'.format(SUPPORT)
BLANK_OR_CORRUPT_TABLE_ERROR = 'Is this a valid instance of this file type?<p>{0}</p>'.format(SUPPORT)
