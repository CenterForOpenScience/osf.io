# -*- coding: utf-8 -*-
import re
import csv
import io
import functools
import string
from math import floor

from django.db.models import Q
from rest_framework.exceptions import NotFound, ValidationError

from osf.models.licenses import NodeLicense
from osf.models import AbstractNode, RegistrationProvider, RegistrationSchema, Institution
from website import settings


METADATA_FIELDS = {'Title': {'format': 'string', 'required': True},
                   'Description': {'format': 'string', 'required': True},
                   'Admin Contributors': {'format': 'list', 'required': True},
                   'Read-Write Contributors': {'format': 'list'},
                   'Read-Only Contributors': {'format': 'list'},
                   'Bibliographic Contributors': {'format': 'list'},
                   'Category': {'format': 'string'},
                   'Affiliated Institutions': {'format': 'list'},
                   'License': {'format': 'object', 'required': True},
                   'Subjects': {'format': 'list', 'required': True},
                   'Tags': {'format': 'list'},
                   'Project GUID': {'format': 'string'},
                   'External ID': {'format': 'string'}}
CONTRIBUTOR_METADATA_FIELDS = ['Admin Contributors',
                               'Read-Write Contributors',
                               'Read-Only Contributors',
                               'Bibliographic Contributors']

CATEGORY_REVERSE_LOOKUP = {display_name: name for name, display_name in settings.NODE_CATEGORY_MAP.items()}

MAX_EXCEL_COLUMN_NUMBER = 16384

STORE = None

@functools.lru_cache(maxsize=MAX_EXCEL_COLUMN_NUMBER)
def get_excel_column_name(column_index):
    column_name = ''
    # Fix zero indexing
    current_column = column_index + 1

    while current_column > 0:
        modulo = (current_column - 1) % 26
        column_name = '{}{}'.format(string.ascii_uppercase[modulo], column_name)
        current_column = floor((current_column - modulo) / 26)

    return column_name

class Store():
    def __init__(self, registration_provider):
        self.licenses = registration_provider.licenses_acceptable.all()
        self.subjects = registration_provider.all_subjects.all()
        self.institutions = Institution.objects.get_all_institutions()

class InvalidHeadersError(ValidationError):
    pass

class BulkRegistrationUpload():
    @property
    def is_valid(self):
        return self.is_validated and not len(self.errors)

    @property
    def is_validated(self):
        return all([row.is_validated for row in self.rows])

    def __init__(self, bulk_upload_csv, provider_id):
        self.raw_csv = bulk_upload_csv.read().decode('utf-8')
        csv_io = io.StringIO(self.raw_csv)
        self.reader = csv.DictReader(csv_io)
        self.headers = self.reader.fieldnames
        schema_id_row = next(self.reader)
        self.schema_id = schema_id_row[self.reader.fieldnames[0]]
        self.provider_id = provider_id

        self.registration_provider = RegistrationProvider.load(self.provider_id)
        if self.registration_provider is None:
            raise NotFound(detail='Registration provider with id "{}" was not found').format(self.provider_id)

        try:
            self.registration_schema = self.registration_provider.schemas.get(_id=self.schema_id)
        except RegistrationSchema.DoesNotExist:
            raise NotFound(detail='Schema with id "{}" was not found'.format(self.schema_id))
        self.schema_questions = BulkRegistrationUpload.get_schema_questions_validations(self.registration_schema)
        self.validations = {**self.schema_questions, **METADATA_FIELDS}
        self.errors = []
        self.validate_csv_header_list()
        self.rows = [Row(row,
                         self.validations,
                         functools.partial(self.log_error, row_index=index + 3))
                     for index, row in enumerate(self.reader)]
        csv_io.close()
        BulkRegistrationUpload.init_store(self.registration_provider)

    @classmethod
    def init_store(cls, registration_provider):
        global STORE
        if STORE is None:
            STORE = Store(registration_provider)

    @classmethod
    def get_schema_questions_validations(cls, registration_schema):
        get_multiple_choice_options = lambda schema_block, schema_blocks: [
            block['display_text']
            for block in schema_blocks
            if block['block_type'] == 'select-input-option'
            and block['schema_block_group_key'] == schema_block['schema_block_group_key']
        ]

        schema_blocks = list(registration_schema.schema_blocks.filter(
            Q(registration_response_key__isnull=False) | Q(block_type='select-input-option')).values(
                'registration_response_key', 'block_type', 'required', 'schema_block_group_key', 'display_text'))

        validations = {}
        for schema_block in schema_blocks:
            if schema_block['block_type'] == 'single-select-input':
                validations.update({
                    schema_block['registration_response_key']: {
                        'type': 'choose',
                        'options': get_multiple_choice_options(schema_block, schema_blocks),
                        'format': 'singleselect',
                        'required': schema_block.get('required'),
                    }
                })
            elif schema_block['block_type'] == 'multi-select-input':
                validations.update({
                    schema_block['registration_response_key']: {
                        'type': 'choose',
                        'options': get_multiple_choice_options(schema_block, schema_blocks),
                        'format': 'multiselect',
                        'required': schema_block.get('required'),
                    }
                })
            elif schema_block['block_type'] in ('short-text-input', 'long-text-input'):
                validations.update({
                    schema_block['registration_response_key']: {
                        'type': 'string',
                        'required': schema_block.get('required'),
                    }
                })
        return validations

    def log_error(self, **kwargs):
        self.errors.append({
            'header': kwargs['header'],
            'column_index': get_excel_column_name(kwargs['column_index']),
            'row_index': kwargs['row_index'],
            'missing': kwargs.get('missing', False),
            'invalid': kwargs.get('invalid', False),
            'external_id': kwargs.get('external_id', ''),
            'type': kwargs.get('type', '')
        })

    def validate_csv_header_list(self):
        expected_headers = self.validations.keys()
        actual_headers = self.headers
        invalid_headers = list(set(actual_headers) - set(expected_headers))
        missing_headers = list(set(expected_headers) - set(actual_headers))
        if invalid_headers or missing_headers:
            raise InvalidHeadersError({'invalid_headers': invalid_headers, 'missing_headers': missing_headers})

    def get_parsed(self):
        parsed = []
        for row in self.rows:
            parsed.append({'csv_raw': row.get_raw_value(), 'csv_parsed': row.get_parsed_value()})
        return {'schema_id': self.schema_id, 'registrations': parsed}

    def validate(self):
        for row in self.rows:
            row.validate()

class Row():
    @property
    def is_validated(self):
        return all([cell.is_validated for cell in self.cells])

    def __init__(self, row_dict, validations, log_error):
        self.row_dict = row_dict
        self.cells = [Cell(header,
                           value, validations[header],
                           functools.partial(log_error, external_id=row_dict.get('External ID', ''), column_index=column_index))
                           for column_index, (header, value) in enumerate(row_dict.items())]

    def get_metadata(self):
        parsed_metadata = {}
        for cell in self.cells:
            if cell.is_metadata:
                parsed_metadata.update(cell.get_parsed_value())
        return parsed_metadata

    def get_registration_responses(self):
        parsed_responses = {}
        for cell in self.cells:
            if not cell.is_metadata:
                parsed_responses.update(cell.get_parsed_value())
        return parsed_responses

    def get_parsed_value(self):
        return {'metadata': self.get_metadata(),
                'registration_responses': self.get_registration_responses()}

    def get_raw_value(self):
        raw_value = io.StringIO()
        cell_values = [cell.value for cell in self.cells]
        csv_writer = csv.writer(raw_value)
        csv_writer.writerow(cell_values)
        return raw_value.getvalue()

    def validate(self):
        for cell in self.cells:
            cell.validate()

class Cell():
    @property
    def is_metadata(self):
        return self.header in METADATA_FIELDS.keys()

    @property
    def is_validated(self):
        return self.field.is_validated

    def __init__(self, header, value, validations, log_error):
        self.header = header
        self.value = value
        self.validations = validations
        self.field = Cell.field_instance_for(self.header,
                                             self.value,
                                             self.validations,
                                             functools.partial(log_error, header=self.header))

    def validate(self):
        self.field.parse()

    def get_parsed_value(self):
        return {self.header: self.field.parse()}

    def get_raw_value(self):
        return self.value

    @classmethod
    def field_instance_for(cls, name, *args):
        field_instance = None
        if name in METADATA_FIELDS.keys():
            if name in CONTRIBUTOR_METADATA_FIELDS:
                field_instance = ContributorField(*args)
            elif name == 'License':
                field_instance = LicenseField(*args)
            elif name == 'Category':
                field_instance = CategoryField(*args)
            elif name == 'Subjects':
                field_instance = SubjectsField(*args)
            elif name == 'Affiliated Institutions':
                field_instance = InstitutionsField(*args)
            elif name == 'Project GUID':
                field_instance = ProjectIDField(*args)
            else:
                field_instance = MetadataField(*args)
        else:
            field_instance = RegistrationResponseField(*args)
        return field_instance


class UploadField():
    def __init__(self):
        self.is_validated = None
        self._parsed_value = None

    def _validate(self):
        raise NotImplementedError('UploadField subclasses must define a _validate method')

    def parse(self):
        if self.is_validated is None:
            self._validate()
            self.is_validated = True
        return self._parsed_value if self._parsed_value is not None else ''

class RegistrationResponseField(UploadField):
    def __init__(self, value, validations, log_error):
        super(RegistrationResponseField, self).__init__()
        self.required = validations.get('required', False)
        self.type = validations.get('type', 'string')
        self.format = validations.get('format')
        self.options = validations.get('options', [])
        self.value = value.strip()
        self.log_error = functools.partial(log_error, type='invalidResponse')

    def get_field_type(self):
        return self.format if self.type == 'choose' else self.type

    def _validate(self):
        parsed_value = None
        if self.required and not bool(self.value):
            self.log_error(missing=True)
        else:
            if not self.value:
                return
            if self.type == 'string':
                parsed_value = self.value
            elif self.type == 'choose' and self.format in ['singleselect', 'multiselect']:
                if self.format == 'singleselect':
                    if self.value not in self.options:
                        self.log_error(invalid=True)
                    else:
                        parsed_value = self.value
                else:
                    parsed_value = []
                    choices = [val.strip() for val in self.value.split(';')]
                    for choice in choices:
                        if choice not in self.options:
                            self.log_error(invalid=True)
                        else:
                            parsed_value.append(choice)
            self._parsed_value = parsed_value

class MetadataField(UploadField):
    def __init__(self, value, validations, log_error):
        super(MetadataField, self).__init__()
        self.format = validations.get('format', 'string')
        self.required = validations.get('required', False)
        self.value = value.strip()
        self.log_error = log_error

    def get_field_type(self):
        return self.format

    def _validate(self):
        parsed_value = None
        if self.required and not bool(self.value):
            self.log_error(missing=True)
        else:
            if self.format == 'string':
                parsed_value = self.value
            elif self.format == 'list':
                parsed_value = [val.strip() for val in self.value.split(';')]
            self._parsed_value = parsed_value

class ContributorField(MetadataField):
    # format: contributor_name<contributor_email>;contributor_name<contributor_email>
    contributor_regex = re.compile(r'(?P<full_name>[\w\W]+)<(?P<email>.*?)>')
    def _validate(self):
        parsed_value = None
        if self.required and not bool(self.value):
            self.log_error(missing=True, type='invalidContributors')
        else:
            if not self.value:
                return
            parsed_value = []
            parsed_contributor_list = [val.strip() for val in self.value.split(';')]
            for contrib in parsed_contributor_list:
                match = self.contributor_regex.match(contrib.strip())
                if match is not None:
                    try:
                        full_name = match.group('full_name')
                        email = match.group('email')
                    except AttributeError:
                        self.log_error(invalid=True, type='invalidContributors')
                    else:
                        parsed_value.append({'full_name': full_name.strip(), 'email': email.strip()})
                else:
                    self.log_error(invalid=True, type='invalidContributors')
            self._parsed_value = parsed_value

class LicenseField(MetadataField):
    # format: license_name;year;copyright_holder_one,copyright_holder_two,...
    with_required_fields_regex = re.compile(r'(?P<name>[\w\W]+);\s*?(?P<year>[1-3][0-9]{3});(?P<copyright_holders>[\w\W]+)')
    no_required_fields_regex = re.compile(r'(?P<name>[\w\W]+)')

    def _validate(self):
        parsed_value = None
        if self.required and not bool(self.value):
            self.log_error(missing=True, type='invalidLicenseName')
        else:
            if not self.value:
                return

            assert hasattr(STORE, 'licenses') is not None, 'STORE.licenses was not initialized!'

            license_name_match = self.no_required_fields_regex.match(self.value)
            if license_name_match is not None:
                node_license_name = license_name_match.group('name')
                try:
                    node_license = STORE.licenses.get(name__iexact=node_license_name)
                except NodeLicense.DoesNotExist:
                    self.log_error(invalid=True, type='invalidLicenseName')
                else:
                    has_required_fields = bool(node_license.properties)
                    if has_required_fields:
                        match = self.with_required_fields_regex.match(self.value)
                        if match is not None:
                            year = match.group('year').strip()
                            copyright_holders = match.group('copyright_holders').strip()
                            copyright_holders = [val.strip() for val in copyright_holders.split(',')]
                            parsed_value = {'name': node_license.name,
                                            'required_fields': {'year': year,
                                                               'copyright_holders': copyright_holders}}
                    else:
                        parsed_value = {'name': node_license.name}
                    self._parsed_value = parsed_value
            else:
                self.log_error(invalid=True, type='invalidLicenseName')

class CategoryField(MetadataField):
    def _validate(self):
        try:
            self._parsed_value = CATEGORY_REVERSE_LOOKUP[self.value if self.value else 'Uncategorized']
        except KeyError:
            self.log_error(invalid=True, type='invalidCategoryName')

class SubjectsField(MetadataField):
    def _validate(self):
        assert hasattr(STORE, 'subjects'), 'STORE.subjects was not initialized!'

        subjects = [val.strip() for val in self.value.split(';')]
        valid_subjects = list(STORE.subjects.filter(text__in=subjects).values_list('text', flat=True))
        invalid_subjects = list(set(subjects) - set(valid_subjects))
        if len(invalid_subjects):
            self.log_error(invalid=True, type='invalidSubjectName')
        else:
            self._parsed_value = valid_subjects

class InstitutionsField(MetadataField):
    def _validate(self):
        if not self.value:
            return

        assert hasattr(STORE, 'institutions'), 'STORE.institutions was not initialized!'

        institutions = [val.strip() for val in self.value.split(';')]
        valid_institutions = list(STORE.institutions.filter(name__in=institutions).values_list('name', flat=True))
        invalid_institutions = list(set(institutions) - set(valid_institutions))
        if len(invalid_institutions):
            self.log_error(invalid=True, type='invalidInstitutionName')
        else:
            self._parsed_value = valid_institutions

class ProjectIDField(MetadataField):
    def _validate(self):
        if not self.value:
            return
        try:
            AbstractNode.objects.get(guids___id=self.value, is_deleted=False, type='osf.node')
        except AbstractNode.DoesNotExist:
            self.log_error(invalid=True, type='invalidProjectId')
        else:
            self._parsed_value = self.value
