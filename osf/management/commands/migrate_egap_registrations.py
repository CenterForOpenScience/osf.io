import logging
import csv
import datetime

from framework.celery_tasks import app as celery_app
from django.db import transaction

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError

import django
django.setup()

from framework.auth.core import Auth
from osf.models import Node, DraftRegistration, OSFUser, RegistrationSchema
from osf_tests.factories import UserFactory
from osf.utils.permissions import WRITE

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CATEGORY = 'project'
VISIBLE = True


def get_egap_schema():
    """Load EGAP Registration Schema
    The EGAP Registration Schema (as of 6/19/19) is not loaded as part of the migrations, but as a management command.
    If you haven't added the EGAP Registration Schema on your environment, run the management command.
    """
    try:
        schema = RegistrationSchema.objects.get(name='EGAP Registration')
    except RegistrationSchema.DoesNotExist:
        raise Exception('EGAP Registration schema has not been created. Please run the `add_egap_registration_schema` management command.')
    return schema

def create_egap_project(title, authors, egap_author):
    """Create OSF Project to back an EGAP registration

    The EGAP Author is added as the project creator.  All other authors are added as unregistered contributors.

    :param title: string, Project/Registration title
    :param authors: string, Comma-separated list of last names
    :param egap_author: OSFUser, project creator
    :return Node: an OSF Project
    """
    project = Node.objects.create(title=title, creator=egap_author, category=CATEGORY)
    authors = authors.split(', ')
    for family_name in authors:
        email = None
        name = family_name.decode('utf-8')

        unregistered_user = OSFUser.create_unregistered(name, email=email)
        unregistered_user.save()

        unregistered_user.add_unclaimed_record(project, referrer=egap_author, given_name=name, email=email)
        project.add_contributor(
            unregistered_user, permissions=WRITE, auth=Auth(egap_author),
            visible=VISIBLE, send_email=False, log=True, save=True
        )
    return project

def build_question_response(header_row, row, question_key, column_title):
    """Format the question's response to go in the registration_metadata
    :param header_row: Header row in spreadsheet
    :param row: Row in spreadsheet
    :param question_key: string, Official question key as part of schema
    :param column_title: string, Corresponding question_key column title in EGAP spreadsheet
    """
    index = header_row.index(column_title)
    value = clean_value(row[index])
    return {
        'comments': [],
        'extra': [],
        'value': value
    }
    return {}

# Need updated spreadsheet so I can account for all the build_question_response
# There are extra spaces in some of the spreadsheet column titles
schema_to_spreadsheet_mapping = [
    {'q1': 'B1 Title of Project'},
    {'q2': 'B2 Author(s)'},
    {'q3': 'ID'},
    {'q4': 'Timestamp'},
    {'q6': 'B4 Is one of the study authors a university faculty member?'},
    {'q8': 'Is this Registration Prospective or Retrospective?'},
    {'q10': 'Is this an experimental study?'},
    {'q11': 'Date of start of study '},
    {'q12': 'Should this study be gated (discouraged)'},
    {'q13': 'Was this design presented at an EGAP meeting?'},
    {'q15': 'C1 Background and explanation of rationale.'},
    {'q16': 'What are the hypotheses to be tested?'},
    {'q17': 'How will these hypotheses be tested?'},
    {'q18': 'C4 Country'},
    {'q19': 'C5 Scale (# of units)'},
    {'q20': 'Was a power analysis conducted prior to data collection?'},
    {'q22': 'Has this research received Insitutional Review Board (IRB) or ethics committee approval?'},
    {'q24': 'C8 IRB Number'},
    {'q25': 'C9 Date of IRB Approval'},
    {'q26': 'Will the intervention be implemented by the researcher or a third party? If a third party, please provide the name. '},
    {'q28': 'Did any of the research team receive remuneration from the implementing agency for taking part in this research? '},
    {'q30': 'If relevant, is there an advance agreement with the implementation group that all results can be published? '},
    {'q32': 'C13 JEL Classifications'},
]

# Any multiple choice questions where "Other" is a possible response, have subsequent "Other"
# question to log that response.  If multiple choice question value is invalid,
# attempt to log the value in the corresponding "Other" question response.
other_mapping = {
    'q6': 'q7',
    'q8': 'q9',
    'q20': 'q21',
    'q22': 'q23',
    'q26': 'q27',
    'q28': 'q29',
    'q30': 'q31'
}

def validate_response(qid, value, draft):
    """Validate question response

    Validating each question response individually.  If there is an error, we will
    attempt to add the value to the subsequent "Other" block.  Return that question id instead.

    :param qid: string, question id from schema
    :param value: question response
    :param draft: DraftRegistration
    :return qid: string
    """
    temporary_check = {}
    temporary_check[qid] = value

    try:
        draft.validate_metadata(temporary_check)
    except ValidationError as exc:
        if qid in other_mapping:
            # TODO, current qid probably needs to be marked as "Other" as well
            return other_mapping[qid]
        else:
            raise Exception(exc)
    return qid

def clean_value(value):
    """Clean spreadsheet values of issues that will affect validation """
    if value == 'n/a':
        return 'N/A'
    elif value == 'Design was registered before field was added':
        return ''
    return value

def build_registraton_metadata(project, header_row, row, egap_author, draft):
    """Build registration metadata dictionary except for file-questions

    :param project Node - node to register
    :param header_row: Header row in spreadsheet
    :param row: Row in spreadsheet
    :param egap_author OSFUser - OSFUser associated with all EGAP registrations
    :param draft: DraftRegistration
    :return registration_metdata: Dictionary
    """
    # TODO Just mark q35 and q36 as True
    registration_metadata = {}

    for question in schema_to_spreadsheet_mapping:
        qid = question.keys()[0]
        column_name = question.values()[0]
        value = build_question_response(header_row, row, qid, column_name)
        validated_qid = validate_response(qid, value, draft)
        registration_metadata[validated_qid] = value

    return registration_metadata

def create_draft_registration(project, egap_author, schema):
    """Create a draft registration with empty metadata
    :param project Node - node to register
    :param egap_author OSFUser - OSFUser associated with all EGAP registrations
    :param schema RegistrationSchema - EGAP Registration Schema
    :return DraftRegistration
    """
    draft_registration = DraftRegistration.create_from_node(
        project,
        user=egap_author,
        schema=schema,
        data={}
    )
    return draft_registration

def make_projects_and_draft_registrations(schema):
    """ Create a project and a draft registration for every row in the EGAP data dump
    For each row in the EGAP dump:
        1) create a project with title, egap authors, and remaining authors.
        2) create an EGAP draft registration linked to the project, copying over all answers to supplemental questions
    :param schema: RegistrationSchema, EGAP
    :return:
    """
    with open('EGAP_registry_forCOS - Registrations.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        header_row = next(csv_reader)

        egap_author = UserFactory()  # TODO, this would need to be the EGAP user
        title_index = header_row.index('B1 Title of Project')
        authors_index = header_row.index('B2 Author(s)')

        for row in csv_reader:
            project = create_egap_project(row[title_index], row[authors_index], egap_author)
            draft_registration = create_draft_registration(project, egap_author, schema)

            registration_metadata = build_registraton_metadata(project, header_row, row, egap_author, draft_registration)
            draft_registration.update_metadata(registration_metadata)
            draft_registration.save()

def upload_files_to_projects(schema):
    """ Programmatically upload files to projects and then update the corresponding draft registration.

    The easiest, most reliable way would be to get a copy of the Dropbox files on your local drive,
    and run a script locally to upload them to their various projects.
    TODO
    """
    pass


def register_projects(schema):
    """Register projects.  Automatically approve?
    TODO
    """
    pass


@celery_app.task(name='management.commands.migrate_egap_registrations')
def main(dry_run=False):
    with transaction.atomic():
        schema = get_egap_schema()
        make_projects_and_draft_registrations(schema=schema)
        upload_files_to_projects(schema=schema)
        register_projects(schema=schema)

        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back.')


class Command(BaseCommand):
    help = '''Migrates EGAP registrations into the system. Assumes 'EGAP_registry_forCOS - Registrations.csv' file in root directory. '''

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

    # Management command handler
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', True)
        script_start_time = datetime.datetime.now()
        logger.info('Script started time: {}'.format(script_start_time))

        main(dry_run)

        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
