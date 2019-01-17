# -*- coding: utf-8 -*-
"""Various text used throughout the website, e.g. status messages, errors, etc.
"""
from website import settings

# Status Messages
#################

# NOTE: in status messages, newlines are not preserved, so triple-quotes strings
# are ok

# Status message shown at settings page on first login
# (upon clicking primary email confirmation link)
WELCOME_MESSAGE = '''
<h1>Welcome to the GakuNin RDM!</h1>
<p>Visit our <a href="http://help.osf.io/" target="_blank" rel="noreferrer">Guides</a> to learn about creating a project, or get inspiration from <a href="https://rdm.nii.ac.jp/explore/activity/#popularPublicProjects">popular public projects</a>.</p>
'''

REGISTRATION_SUCCESS = '''Registration successful. Please check {email} to confirm your email address.'''

EXTERNAL_LOGIN_EMAIL_CREATE_SUCCESS = '''A new OSF account has been created with your {external_id_provider} profile. Please check {email} to confirm your email address.'''

EXTERNAL_LOGIN_EMAIL_LINK_SUCCESS = '''Your OSF account has been linked with your {external_id_provider}. Please check {email} to confirm this action.'''

# Shown if registration is turned off in website.settings
REGISTRATION_UNAVAILABLE = 'Registration currently unavailable.'

ALREADY_REGISTERED = u'The email {email} has already been registered.'

AFTER_SUBMIT_FOR_REVIEW = 'Your submission has been received. You will be notified within two business days regarding the status of your submission. If you have questions you may contact us at prereg@cos.io.'

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

# Shown at login page if user tries to access a resource that requires auth
MUST_LOGIN = '''
You must log in or create a new account to claim the contributor-ship.
'''

# Shown on logout
LOGOUT = '''
You have successfully logged out.
'''

EMAIL_NOT_FOUND = u'''
{email} was not found in our records.
'''

# Shown after an unregistered user claims an account and is redirected to the
# settings page
CLAIMED_CONTRIBUTOR = ('<strong>Welcome to the GakuNin RDM!</strong> Edit your display name below and then check your '
                       '<a href="/dashboard/">dashboard</a> to see projects to which you have been added as a '
                       'contributor by someone else.')

# Error Pages
# ###########

# Search-related errors
SEARCH_QUERY_HELP = ('Please check our help (the question mark beside the search box) for more information '
                     'on advanced search queries.')

# Shown at error page if an expired/revokes email confirmation link is clicked
EXPIRED_EMAIL_CONFIRM_TOKEN = 'This confirmation link has expired. Please <a href="/login/">log in</a> to continue.'

INVALID_EMAIL_CONFIRM_TOKEN = 'This confirmation link is invalid. Please <a href="/login/">log in</a> to continue.'

CANNOT_MERGE_ACCOUNTS_SHORT = 'Cannot Merge Accounts'

CANNOT_MERGE_ACCOUNTS_LONG = (
    'Accounts cannot be merged due to a possible conflict with add-ons.  '
    'Before you continue, please <a href="/settings/addons/"> deactivate '
    'any add-ons</a> to be merged into your primary account.'
)

MERGE_COMPLETE = 'Accounts successfully merged.'

MERGE_CONFIRMATION_REQUIRED_SHORT = 'Confirmation Required: Merge Accounts'

MERGE_CONFIRMATION_REQUIRED_LONG = (
    u'<p>This email is confirmed to another account. '
    u'Would you like to merge <em>{src_user}</em> with the account '
    u'<em>{dest_user}</em>?<p>'
    u'<a class="btn btn-primary" href="?confirm_merge">Confirm merge</a> '
)

# Node Actions

AFTER_REGISTER_ARCHIVING = (
    'Files are being copied to the newly created registration, and you will receive an email '
    'notification when the copying is finished.'
)

BEFORE_REGISTER_HAS_POINTERS = (
    u'This {category} contains links to other projects. Links will be copied '
    u'into your registration, but the projects that they link to will not be '
    u'registered. If you wish to register the linked projects, you must fork '
    u'them from the original project before registering.'
)

BEFORE_FORK_HAS_POINTERS = (
    u'This {category} contains links to other projects. Links will be copied '
    u'into your fork, but the projects that they link to will not be forked. '
    u'If you wish to fork the linked projects, they need to be forked from the '
    u'original project.'
)

REGISTRATION_INFO = '''
<p>Registration creates a frozen version of the project that can never be
edited or deleted but can be withdrawn. You can register your project by
selecting a registration form, entering information about your project, and
then confirming. You will be able to continue editing the original project,
however, and the frozen version with timestamps will always be linked to
the original. Withdrawing a registration will leave behind metadata about
when the registration was created and withdrawn but removes the contents
of the registration.</p>

<ul>
    <li>A registration can be made public immediately or entered into
    an embargo period of up to four years. At the end of the embargo period,
    the registration will automatically become public.</li>

    <li>Before initiating a registration, make sure that the project is
    in the state that you wish to freeze. Consider turning links into
    forks.</li>

    <li>Start by selecting a registration form from the list below. You can hit
    your browser's back button if the selected form is not appropriate for
    your use.</li>
</ul>
'''

REGISTRATION_EMBARGO_INFO = '''
You can choose whether to make your registration public immediately or
embargo it for up to four years. At the end of the embargo period the registration
is automatically made public. After becoming public, the only way to remove a
registration is to withdraw it. Withdrawn registrations show only the registration title,
contributors, and description to indicate that a registration was made and
later withdrawn.
<br /><br />
If you choose to embargo your registration, a notification will be sent to
all other project contributors. Other administrators will have 48 hours to
approve or cancel creating the registration. If any other administrator rejects the
registration, it will be canceled. If all other administrators approve or do
nothing, the registration will be confirmed and enter its embargo period.
'''

BEFORE_REGISTRATION_INFO = '''
Registration cannot be undone, and the archived content and files cannot be
deleted after registration. Please be sure the project is complete and
comprehensive for what you wish to register.
'''

# Nodes: forking, templating, linking

LINK_ACTION = 'Link to this Project'
LINK_DESCRIPTION = """
<p>Linking to this project will reference it in another project, without
creating a copy. The link will always point to the most up-to-date version.</p>
"""

TEMPLATE_ACTION = 'Duplicate template'
TEMPLATE_DESCRIPTION = """
<p>This option will create a new project, using this project as a template.
The new project will be structured in the same way, but contain no data.</p>
"""

FORK_ACTION = 'Fork this Project'
FORK_DESCRIPTION = """
<p>Fork this project if you plan to build upon it in your own work.
The new project will be an exact duplicate of this project's current state,
with you as the only contributor.</p>
"""

TEMPLATE_DROPDOWN_HELP = """Start typing to search. Selecting project as
template will duplicate its structure in the new project without importing the
content of that project."""

TEMPLATED_FROM_PREFIX = 'Templated from '

# MFR Error handling
ERROR_PREFIX = "Unable to render. <a href='?action=download'>Download</a> file to view it."
SUPPORT = u"Contact " + settings.OSF_SUPPORT_EMAIL + u"for further assistance."

SUPPORT_LINK = 'please report it to <a href="mailto:' + settings.OSF_SUPPORT_EMAIL + '">' + settings.OSF_SUPPORT_EMAIL + '</a>.'

# Custom Error Messages w/ support  # TODO: Where are these used? See [#OSF-6101]
STATA_VERSION_ERROR = u'Version of given Stata file is not 104, 105, 108, 113 (Stata 8/9), 114 (Stata 10/11) or 115 (Stata 12)<p>{0}</p>'.format(SUPPORT)
BLANK_OR_CORRUPT_TABLE_ERROR = u'Is this a valid instance of this file type?<p>{0}</p>'.format(SUPPORT)

#disk saving mode
DISK_SAVING_MODE = 'Forks, registrations, and uploads to OSF Storage uploads are temporarily disabled while we are undergoing a server upgrade. These features will return shortly.'

#log out and revisit the link to confirm emails
CONFIRM_ALTERNATE_EMAIL_ERROR = 'The email address has <b>NOT</b> been added to your account. Please log out and revisit the link in your email. Thank you.'
