import sys
import logging

from website.app import setup_django
setup_django()

from website import settings
from scripts import utils as script_utils
from osf.models import MetaSchema, Contributor, Registration
from framework.email.tasks import send_email

logger = logging.getLogger(__name__)


EMAIL_TEXT = """

Hi -

We are writing to you to briefly inquire about the status of your entry in the 2016 Election Research Preacceptance Competition (ERPC).

Please take this brief survey now: https://dartmouth.co1.qualtrics.com/jfe/form/SV_892z7o3XngHhuYJ . It will take approximately five minutes and would be immensely helpful to us in learning both about the status of your entry and what about the ERPC did or did not work well. Thank you!

Sincerely,

Skip and Brendan


*Arthur Lupia*

Institute for Social Research and Department of Political Science, University of Michigan

Chair, The National Academies Roundtable on the Communication and Use of Behavioral and Social Sciences

Chairman of the Board, Center for Open Science

http://www.arthurlupia.com

lupia@umich.edu

Twitter: @ArthurLupia


*Brendan Nyhan*

Professor of Government

Dartmouth College

nyhan@dartmouth.edu

http://www.dartmouth.edu/~nyhan

"""


def get_erpc_participants(dry=True):
    """
        :param dry: Also include the email addresses for the ERPC Administrators.

        :return: A list of emails for anyone who has admin + read/write to a registration created
        with the ERPC registration schema
    """
    erpc_metaschema = MetaSchema.objects.get(name='Election Research Preacceptance Competition', active=False)
    registrations = Registration.objects.filter(registered_schema=erpc_metaschema)

    participants_to_email = []
    for registration in registrations:
        contributors = Contributor.objects.filter(node=registration).only('user')
        for contributor in contributors:
            if contributor.write or contributor.admin:
                participants_to_email.append(contributor.user.username)

    if not dry:
        participants_to_email += ['lupia@umich.edu', 'brendan.j.nyhan@dartmouth.edu']

    return participants_to_email


def send_email_to_erpc_participants(participants, dry=True):
    from_addr = settings.FROM_EMAIL
    subject = 'ERPC user survey - help us learn how to improve preacceptance!'

    participants = set(participants)

    logger.info('About to send an email to {} ERPC participants'.format(len(participants)))

    for participant in participants:
        if not dry:
            logger.info('Sending to {}'.format(participant))
            send_email(from_addr=from_addr, to_addr=participant, subject=subject, mimetype='text', message=EMAIL_TEXT, username=settings.MAIL_USERNAME, password=settings.MAIL_PASSWORD)
        else:
            logger.info('Would have sent an email to {}'.format(participant))

def main(dry):
    participants = get_erpc_participants(dry)
    send_email_to_erpc_participants(participants, dry)


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
