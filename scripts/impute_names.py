"""
Email users to verify citation information.
"""

from framework.auth.utils import parse_name
from framework.email.tasks import send_email

from website.app import init_app
from website import models
from website import settings

app = init_app('website.settings', set_backends=True, routes=True)

email_template = '''Hello, {fullname},\n
\n
Along with a shorter domain name (https://osf.io), the Open Science Framework
has recently introduced a citation widget on project and component dashboards.\n
\n
As such, we are expanding user settings to include Citation Style Language name
specifications that will allow us to accurately produce said citations.\n
\n
Based upon your full name, "{fullname}", we've done our best to automatically infer the following:\n
\n
Given name: {given_name}\n
Middle name(s): {middle_names}\n
Family name: {family_name}\n
Suffix: {suffix}\n
\n
If this information is correct, you don't need to do anything. If you'd like
to make an adjustment or test the parsing, please browse to\n
\n
https://osf.io/settings\n
\n
and correct these values. If you have any questions or comments about this, please contact
us at feedback@osf.io (don't reply to this email).\n
\n
I remain sincerely yours,\n
\n
The OSF Robot.
'''

def email_name(user):

    names = parse_name(user)

    send_email.delay(
        from_addr=settings.FROM_EMAIL,
        to_addr=user.username,
        subject='OSF: Verify your citation information',
        message=email_template.format(**names),
    )

#def email_names():
#
#    for user in models.User.find():
#        email_name(user)

#def impute_names(out):
#
#    with open(out, 'w') as fp:
#        for user in models.User.find():
#            names = parse_name(user.fullname)
#            fp.write(u'\t'.join([
#                names['given_name'],
#                names['middle_names'],
#                names['family_name'],
#                names['suffix'],
#            ]).encode('utf-8'))
#            fp.write('\n')
#
#if __name__ == '__main__':
#    impute_names('names.tsv')