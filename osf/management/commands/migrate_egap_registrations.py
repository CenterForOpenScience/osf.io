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
    authors = authors.split(',')
    for family_name in authors:
        # TODO - supplement email from email list
        email = None
        name = family_name

        unregistered_user = OSFUser.create_unregistered(name, email=email)
        unregistered_user.save()

        unregistered_user.add_unclaimed_record(project, referrer=egap_author, given_name=name, email=email)
        # Give every EGAP author WRITE permissions, and make them bibliographic.
        project.add_contributor(
            unregistered_user, permissions=WRITE, auth=Auth(egap_author),
            visible=VISIBLE, send_email=False, log=True, save=True
        )

    # Make EGAP author non-bibliographic
    project.update_contributor(egap_author, permission='admin', visible=False, auth=Auth(egap_author), save=True)
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
    # Spreadsheet has these as comma-separated values, but looking for array
    if question_key in ['q33', 'q34']:
        value = value.split(', ')
    return build_nested_response(value)

def build_nested_response(value):
    return {
        'comments': [],
        'extra': [],
        'value': value
    }

schema_to_spreadsheet_mapping = [
    {'q1': 'TITLE'},
    {'q2': 'B2 AUTHORS'},
    {'q3': 'ID'},
    {'q4': 'POST DATE'},
    {'q5': 'B3 ACKNOWLEDGEMENTS'},
    {'q6': 'B4 FACULTY MEMBER?'},
    {'q8': 'B5 PROSPECTIVE OR RETROSPECTIVE?'},
    {'q10': 'B6 EXPERIMENTAL STUDY?'},
    {'q11': 'B7 DATE OF START OF STUDY'},
    {'q12': 'B8 GATE DATE'},
    {'q13': 'B9 PRESENTED AT EGAP MEETING?'},
    {'q14': 'B10 PRE-ANALYSIS PLAN WITH REGISTRATION?'},
    {'q15': 'C1 BACKGROUND'},
    {'q16': 'C2 HYPOTHESES'},
    {'q17': 'C3 TESTING PLAN'},
    {'q18': 'C4 COUNTRY'},
    {'q19': 'C5 SAMPLE SIZE'},
    {'q20': 'C6 POWER ANALYSIS?'},
    {'q22': 'C7 IRB APPROVAL?'},
    {'q24': 'C8 IRB NUMBER'},
    {'q25': 'C9 DATE OF IRB APPROVAL'},
    {'q26': 'C10 INTERVENTION IMPLEMENTER'},
    {'q28': 'C11 REMUNERATION?'},
    {'q30': 'C12 PUBLICATION AGREEMENT?'},
    {'q32': 'C13 JEL CODES'},
    {'q33': 'METHODOLOGY'},
    {'q34': 'POLICY'},
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
    attempt to add the value to the corresponding "Other" block.  Return that question id instead.

    For example, q6 is a multiple choice question, with "Other" as a choice.  If text is entered
    for q6 that does not match one of the multiple choice answers, assuming that this is "other"
    text, and this response should go to the corresponding q7 question.  q6 will be marked
    as "Other"

    :param qid: string, question id from schema
    :param value: question response
    :param draft: DraftRegistration
    :return qid: tuple, (qid corresponding to value, optional "Other" qid)
    """
    temporary_check = {}
    temporary_check[qid] = value

    try:
        draft.validate_metadata(temporary_check)
    except ValidationError as exc:
        if qid in other_mapping:
            return other_mapping[qid], qid
        else:
            raise Exception(exc)
    return qid, None

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
    registration_metadata = {}

    for question in schema_to_spreadsheet_mapping:
        qid = question.keys()[0]
        column_name = question.values()[0]
        value = build_question_response(header_row, row, qid, column_name)
        validated_qid, other_response = validate_response(qid, value, draft)
        registration_metadata[validated_qid] = value
        if other_response:
            registration_metadata[other_response] = build_nested_response('Other (describe in text box below)')

    # q35 and q36 are required questions at the end of the schema, certification and
    # confirmation questions. Just marking as agree -
    registration_metadata['q35'] = build_nested_response('Agree')
    registration_metadata['q36'] = build_nested_response('Agree')
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
    with open('egap_registry_for_cos.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        header_row = next(csv_reader)
        normalized_header_row = [col_header.decode('ascii', 'ignore') for col_header in header_row]

        egap_author = UserFactory()  # TODO, this would need to be the EGAP user (Matthew Lisiecki)
        title_index = normalized_header_row.index('TITLE')
        authors_index = normalized_header_row.index('B2 AUTHORS')

        for line in csv_reader:
            row = [cell.decode('ascii', 'ignore').strip() for cell in line]
            project = create_egap_project(row[title_index], row[authors_index], egap_author)
            draft_registration = create_draft_registration(project, egap_author, schema)

            registration_metadata = build_registraton_metadata(project, normalized_header_row, row, egap_author, draft_registration)
            draft_registration.update_metadata(registration_metadata)
            draft_registration.save()

def upload_files_to_projects(schema):
    """ Programmatically upload files to projects and then update the corresponding draft registration.

    The easiest, most reliable way would be to get a copy of the Dropbox files on your local drive,
    and run a script locally to upload them to their various projects.
    TODO - probably call with a separate argument as part of the management command
    """
    pass


def register_projects(schema):
    """Register projects.  Automatically approve.
    TODO - probably call with a separate argument as part of the management command
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
