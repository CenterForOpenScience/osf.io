import logging
import csv
import datetime
import json
import os
import shutil
import jsonschema
import argparse

from jsonschema.exceptions import ValidationError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--authorsource', help='Specify the source file for the author csv file')
parser.add_argument('-r', '--registrysource', help='Specify the source file for the registrty csv file')
parser.add_argument('-t', '--target', help='Specify the target directory of the registry directories')
parser.add_argument('-d', '--dry', action='store_true', help='Dry run: Have the script delete the target directory after completion')

schema_to_spreadsheet_mapping = [
    {'q1': 'TITLE'},
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


here = os.path.split(os.path.abspath(__file__))[0]


def from_json(fname):
    with open(os.path.join(here, fname)) as f:
        return json.load(f)


def ensure_schema_structure(schema):
    schema['pages'] = schema.get('pages', [])
    schema['title'] = schema['name']
    schema['version'] = schema.get('version', 1)
    return schema


def create_file_tree_and_json(author_source, registry_source, target):
    # Things this function needs to do:
    # For each row in the registry function, create a directory.
    # Create two JSON files, one project json with ID, Title, Postdate, and authors listed
    # with emails. And another with all the key value pairs for the registry meta.
    top_dir = target
    logger.info('Creating EGAP directory at {}'.format(top_dir))
    os.mkdir(top_dir)
    author_list = create_author_dict(author_source)
    with open(registry_source, 'rt', encoding='utf-8-sig') as csv_registry_file:
        csv_reader = csv.reader(csv_registry_file, delimiter=',')
        header_row = next(csv_reader)
        normalized_header_row = [col_header.strip() for col_header in header_row]
        logger.info('Debug data')
        logger.info('Header row: {}'.format(header_row))
        logger.info('Normalized header row: {}'.format(normalized_header_row))

        id_index = normalized_header_row.index('ID')
        for line in csv_reader:
            row = [cell for cell in line]
            project_id = row[id_index]
            root_directory = os.path.join(top_dir, project_id)
            os.mkdir(root_directory)
            data_directory = os.path.join(root_directory, 'data')
            os.mkdir(data_directory)
            os.mkdir(os.path.join(data_directory, 'nonanonymous'))
            project_dict = make_project_dict(row, author_list, normalized_header_row)
            make_json_file(root_directory, project_dict, 'project')
            try:
                registration_dict = make_registration_dict(row, normalized_header_row, project_id)
            except Exception:
                logger.warning('Error creating directory for {}'.format(project_id))
                shutil.rmtree(root_directory)
                continue
            make_json_file(root_directory, registration_dict, 'registration')
            logger.info('Successfully created directory for {}'.format(project_id))



def create_author_dict(source):
    # Reads in author CSV and returns a list of dicts with names and emails of EGAP Authors
    authors = []
    with open(source, 'rt', encoding='utf-8-sig') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        header_row = next(csv_reader)
        normalized_header_row = [col_header.strip() for col_header in header_row]
        logger.info('Debug data')
        logger.info('Header row: {}'.format(header_row))
        logger.info('Normalized header row: {}'.format(normalized_header_row))
        name_index = normalized_header_row.index('Name')
        email_index = normalized_header_row.index('Email')
        for line in csv_reader:
            row = [cell for cell in line]
            logger.info('Adding user: ' + row[name_index])
            if row[email_index] != '':
                author_dict = {'name': row[name_index].strip(), 'email': row[email_index]}
            else:
                author_dict = {'name': row[name_index].strip()}
            authors.append(author_dict)
    return authors


def make_project_dict(row, author_list, normalized_header_row):
    project = {}
    title_index = normalized_header_row.index('TITLE')
    id_index = normalized_header_row.index('ID')
    postdate_index = normalized_header_row.index('POST DATE')
    contributors_index = normalized_header_row.index('B2 AUTHORS')
    project['id'] = row[id_index]
    project['title'] = row[title_index]
    project['post-date'] = row[postdate_index]

    authors = row[contributors_index]

    authors = authors.split('|')
    project['contributors'] = []
    author_name_list = [author['name'] for author in author_list]
    for author in authors:
        author = author.strip()
        if author:
            if author not in author_name_list:
                logger.warning('Author {} not in Author spreadsheet for project {}.'.format(author,row[id_index]))
                project['contributors'].append({'name': author})
            else:
                author_list_index = author_name_list.index(author)
                project['contributors'].append(author_list[author_list_index])
    return project


def make_registration_dict(row, normalized_header_row, project_id):
    registration = {}

    for question in schema_to_spreadsheet_mapping:
        qid = list(question.keys())[0]
        column_name = list(question.values())[0]
        value = build_question_response(normalized_header_row, row, qid, column_name)
        if value['value'] == '':
            continue
        validated_qid, other_response = validate_response(qid, value)

        if other_response == 'q26':
            if other_response:
                responses = []
                if value['value'][0].startswith('Researchers,'):
                    responses.append('Researchers')
                responses.append('Third party (describe in text box below)')
                registration[other_response] = build_nested_response(responses)
                value['value'] = value['value'][0]
        elif other_response:
            registration[other_response] = build_nested_response('Other (describe in text box below)')
        registration[validated_qid] = value
    # q35 and q36 are required questions at the end of the schema, certification and
    # confirmation questions. Just marking as agree -
    registration['q35'] = build_nested_response('Agree')
    registration['q36'] = build_nested_response('Agree')
    validate_all_responses(registration, project_id)
    return registration


def make_json_file(filepath, data, json_type):
    if json_type == 'project':
        filepath = filepath + '/project.json'
    if json_type == 'registration':
        filepath = filepath + '/registration-schema.json'
    with open(filepath, 'w') as outfile:
        json.dump(data, outfile)


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
    if question_key == 'q26':
        value = [value]
    if question_key in ['q33', 'q34']:
        value = value.split(', ')
    return build_nested_response(value)


def clean_value(value):
    """Clean spreadsheet values of issues that will affect validation """
    if value == 'n/a':
        return 'N/A'
    elif value == 'Design was registered before field was added':
        return ''
    return value

def build_nested_response(value):
    return {
        'comments': [],
        'extra': [],
        'value': value
    }


def base_metaschema(metaschema):
    json_schema = {
        'type': 'object',
        'description': metaschema['description'],
        'title': metaschema['title'],
        'additionalProperties': False,
        'properties': {
        }
    }
    return json_schema


def get_required(question):
    """
    Returns True if metaschema question is required.
    """
    required = question.get('required', False)
    if not required:
        properties = question.get('properties', False)
        if properties and isinstance(properties, list):
            for item, property in enumerate(properties):
                if isinstance(property, dict) and property.get('required', False):
                    required = True
                    break
    return required


COMMENTS_SCHEMA = {
    'type': 'array',
    'items': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'seenBy': {
                'type': 'array',
            },
            'canDelete': {'type': 'boolean'},
            'created': {'type': 'string'},
            'lastModified': {'type': 'string'},
            'author': {'type': 'string'},
            'value': {'type': 'string'},
            'isOwner': {'type': 'boolean'},
            'getAuthor': {'type': 'string'},
            'user': {
                'type': 'object',
                'additionalProperties': True,
                'properties': {
                    'fullname': {'type': 'string'},
                    'id': {'type': 'integer'}
                }
            },
            'saved': {'type': 'boolean'},
            'canEdit': {'type': 'boolean'},
            'isDeleted': {'type': 'boolean'}
        }
    }
}


def get_options_jsonschema(options, required):
    """
    Returns multiple choice options for schema questions
    """
    for item, option in enumerate(options):
        if isinstance(option, dict) and option.get('text'):
            options[item] = option.get('text')
    value = {'enum': options}

    if not required and '' not in value['enum']:  # Non-required fields need to accept empty strings as a value.
        value['enum'].append('')

    return value


def get_object_jsonschema(question, required_fields, is_reviewer, is_required):
    """
    Returns jsonschema for nested objects within schema
    """
    object_jsonschema = {
        'type': 'object',
        'additionalProperties': False,
        'properties': {

        }
    }
    required = []
    properties = question.get('properties')
    if properties:
        for property in properties:
            if property.get('required', False) and required_fields:
                required.append(property['id'])
            values = extract_question_values(property, required_fields, is_reviewer, is_required)
            object_jsonschema['properties'][property['id']] = {
                'type': 'object',
                'additionalProperties': False,
                'properties': values
            }
            if required_fields:
                object_jsonschema['properties'][property['id']]['required'] = ['value']
    if required_fields and is_required:
        object_jsonschema['required'] = required

    return object_jsonschema


OSF_UPLOAD_EXTRA_SCHEMA = {
    'type': 'array',
    'items': {
        'type': 'object',
        'additionalProperties': False,
        'properties': {
            'data': {
                'type': 'object',
                'additionalProperties': False,
                'properties': {
                    'kind': {'type': 'string'},
                    'contentType': {'type': 'string'},
                    'name': {'type': 'string'},
                    'extra': {
                        'type': 'object',
                        'additionalProperties': False,
                        'properties': {
                            'downloads': {'type': 'integer'},
                            'version': {'type': 'integer'},
                            'latestVersionSeen': {'type': 'string'},
                            'guid': {'type': 'string'},
                            'checkout': {'type': 'string'},
                            'hashes': {
                                'type': 'object',
                                'additionalProperties': False,
                                'properties': {
                                    'sha256': {'type': 'string'},
                                    'md5': {'type': 'string'}
                                }
                            }
                        }
                    },
                    'materialized': {'type': 'string'},
                    'modified': {'type': 'string'},
                    'nodeId': {'type': 'string'},
                    'etag': {'type': 'string'},
                    'provider': {'type': 'string'},
                    'path': {'type': 'string'},
                    'nodeUrl': {'type': 'string'},
                    'waterbutlerURL': {'type': 'string'},
                    'resource': {'type': 'string'},
                    'nodeApiUrl': {'type': 'string'},
                    'type': {'type': 'string'},
                    'accept': {
                        'type': 'object',
                        'additionalProperties': False,
                        'properties': {
                            'acceptedFiles': {'type': 'boolean'},
                            'maxSize': {'type': 'integer'},
                        }
                    },
                    'links': {
                        'type': 'object',
                        'additionalProperties': False,
                        'properties': {
                            'download': {'type': 'string'},
                            'move': {'type': 'string'},
                            'upload': {'type': 'string'},
                            'delete': {'type': 'string'}
                        }
                    },
                    'permissions': {
                        'type': 'object',
                        'additionalProperties': False,
                        'properties': {
                            'edit': {'type': 'boolean'},
                            'view': {'type': 'boolean'}
                        }
                    },
                    'created_utc': {'type': 'string'},
                    'id': {'type': 'string'},
                    'modified_utc': {'type': 'string'},
                    'size': {'type': 'integer'},
                    'sizeInt': {'type': 'integer'},
                }
            },
            'fileId': {'type': ['string', 'object']},
            'descriptionValue': {'type': 'string'},
            'sha256': {'type': 'string'},
            'selectedFileName': {'type': 'string'},
            'nodeId': {'type': 'string'},
            'viewUrl': {'type': 'string'}
        }
    }
}


def extract_question_values(question, required_fields, is_reviewer, is_required):
    """
    Pulls structure for 'value', 'comments', and 'extra' items
    """
    response = {
        'value': {'type': 'string'},
        'comments': COMMENTS_SCHEMA,
        'extra': {'type': 'array'}
    }
    if question.get('type') == 'object':
        response['value'] = get_object_jsonschema(question, required_fields, is_reviewer, is_required)
    elif question.get('type') == 'choose':
        options = question.get('options')
        if options:
            enum_options = get_options_jsonschema(options, is_required)
            if question.get('format') == 'singleselect':
                response['value'] = enum_options
            elif question.get('format') == 'multiselect':
                response['value'] = {'type': 'array', 'items': enum_options}
    elif question.get('type') == 'osf-upload':
        response['extra'] = OSF_UPLOAD_EXTRA_SCHEMA

    if is_reviewer:
        del response['extra']
        if not question.get('type') == 'object':
            del response['value']

    return response


def create_jsonschema_from_metaschema(metaschema, required_fields=False, is_reviewer=False):
    """
    Creates jsonschema from registration metaschema for validation.

    Reviewer schemas only allow comment fields.
    """
    json_schema = base_metaschema(metaschema)
    required = []

    for page in metaschema['pages']:
        for question in page['questions']:
            is_required = get_required(question)
            if is_required and required_fields:
                required.append(question['qid'])
            json_schema['properties'][question['qid']] = {
                'type': 'object',
                'additionalProperties': False,
                'properties': extract_question_values(question, required_fields, is_reviewer, is_required)
            }
            if required_fields:
                json_schema['properties'][question['qid']]['required'] = ['value']

        if required and required_fields:
            json_schema['required'] = required

    return json_schema


def validate_response(qid, value):
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
    egap_schema = ensure_schema_structure(from_json('egap-registration-3.json'))
    schema = create_jsonschema_from_metaschema(egap_schema,
        required_fields=False,
        is_reviewer=False)

    try:
        json_schema = jsonschema.validate(temporary_check, schema)
    except ValidationError as exc:
        if qid in other_mapping:
            return other_mapping[qid], qid
        else:
            raise Exception(exc)
    return qid, None

def validate_all_responses(value, project_id):
    egap_schema = ensure_schema_structure(from_json('egap-registration-3.json'))
    schema = create_jsonschema_from_metaschema(egap_schema,
        required_fields=True,
        is_reviewer=False)

    try:
        json_schema = jsonschema.validate(value, schema)
    except ValidationError as exc:
        with open('errors.txt', 'a+') as error_file:
            error_file.write(', '+project_id)
        raise Exception(exc)


def main(default_args=False):
    if default_args:
        args = parser.parse_args(['--source', 'default', '--target', 'default'])
    else:
        args = parser.parse_args()

    author_source = args.authorsource
    registry_source = args.registrysource
    target_directory = args.target
    dry_run = args.dry

    if not author_source:
        author_source = 'EGAP_author_emails.csv'

    if not registry_source:
        registry_source = 'EGAP_registry_for_OSF.csv'

    if not target_directory:
        target_directory = 'EGAP_data_{}'.format(datetime.datetime.now().strftime('%m-%d-%Y'))

    create_file_tree_and_json(author_source, registry_source, target_directory)

    if dry_run:
        shutil.rmtree(target_directory)
        raise RuntimeError('Dry run, file tree being deleted.')


if __name__ == '__main__':

    main(default_args=False)
