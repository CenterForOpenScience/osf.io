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

Dear ERPC participants,

Thanks so much for registering a design for the Election Research Preacceptance Competition. We are writing to clarify the competition rules now that the ANES data have been publicly released.

Even if you have not yet submitted an article based on your design, you can still publish your findings and win a cash prize as long as your paper includes an analysis of your preregistered design and clearly indicates any difference between the submitted design and any subsequent exploratory analyses. At this point in the competition, preacceptance is no longer a necessary condition for being published at a participating journal or winning a prize.

We have worked with all of the participating editors to learn about how they wish to receive ERPC manuscripts going forward. Here are their preferences:

- Political Behavior and Public Opinion Quarterly would like you to submit ERPC manuscripts *without* the data or analyses (in other words, they want to review the article under preacceptance conditions).

- American Journal of Political Science, American Politics Research, Political Analysis, and Political Science Quarterly prefer that you submit ERPC manuscripts *with* the data or analyses (in other words, they want to review manuscripts than include your pre-registered designs, but not under conditions of preacceptance).

- American Political Science Review and State Politics and Policy Quarterly will accept your ERPC manuscript for review with or without the data.

Political Science Research and Methods has not yet indicated its preferences; please contact the editor for clarification before submitting an article to them.

To be eligible for a prize, we ask that you submit the initial version of your article to a partner journal no later than January 31, 2018.

Thank you for your consideration and thank you for participating in the ERPC. Please let us know if you have any additional questions.

Sincerely,

Brendan and Skip


*IMPORTANT NOTICE ABOUT YOUR CONTACT INFORMATION*:
If you would like to be contacted directly by Brendan and Skip, please share your email address via this google form: https://goo.gl/forms/kgIHxTpL6a7vqmDF2



*Brendan Nyhan*

Professor of Government

Dartmouth College

nyhan@dartmouth.edu

http://www.dartmouth.edu/~nyhan

*Arthur Lupia*

Institute for Social Research and Department of Political Science, University of Michigan

Chair, The National Academies Roundtable on the Communication and Use of Behavioral and Social Sciences

Chairman of the Board, Center for Open Science

http://www.arthurlupia.com

lupia@umich.edu

Twitter: @ArthurLupia

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
    subject = 'Publishing results of ANES analyses for Election Research Pre-acceptance Competition'

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
