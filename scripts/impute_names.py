"""
Email users to verify citation information.
"""

import re
import logging

from framework.auth.utils import impute_names
from framework.email.tasks import send_email

from website.app import init_app
from website import models

app = init_app('website.settings', set_backends=True, routes=True)

logging.basicConfig(filename='impute_names.log', level=logging.DEBUG)

email_template = u'''Hello, {fullname},


Along with a shorter domain name (http://osf.io), the Open Science Framework
has recently introduced a citation widget on project and component dashboards.


As such, we are expanding user settings to include Citation Style Language name
specifications that will allow us to accurately produce these citations. Your full
name can be different than the parts of the name used in citations.


Based upon your full name, "{fullname}", we've done our best to automatically infer the following:


Given name: {given_name}

Middle name(s): {middle_names}

Family name: {family_name}

Suffix: {suffix}


If this information is correct, you don't need to do anything. If you'd like
to make an adjustment or test the parsing algorithm, please browse to


http://osf.io/settings


If you have any questions or comments, please contact us at feedback+citations@osf.io (don't reply to this email).


I remain,


Sincerely yours,


The OSF Robot.
'''

def clean_template(template):
    cleaned = ''
    for line in template.splitlines():
        cleaned += line or '\n'
    cleaned = re.sub(' +', ' ', cleaned)
    return cleaned

email_template = clean_template(email_template)

def email_name(user):

    logging.debug('Emailing user {0}'.format(user.fullname))

    names = {'fullname': user.fullname}
    names.update(impute_names(user.fullname))

    message=email_template.format(**names).encode('utf-8')

    success = send_email(
        from_addr='openscienceframework-robot@osf.io',
        to_addr=user.username,
        subject='Open Science Framework: Verify your citation information',
        message=message,
        mimetype='plain',
    )

    if success:
        logging.debug('Emailing user {0}: Success'.format(user.fullname))
    else:
        logging.debug('Emailing user {0}: Failure'.format(user.fullname))

def email_names():

    for user in models.User.find():
        email_name(user)

#if __name__ == '__main__':
#    impute_names('names.tsv')
