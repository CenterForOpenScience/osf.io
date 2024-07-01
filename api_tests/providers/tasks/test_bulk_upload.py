from unittest import mock
import pytest
import uuid

from api.providers.tasks import bulk_create_registrations

from osf.exceptions import RegistrationBulkCreationContributorError, RegistrationBulkCreationRowError
from osf.models import RegistrationBulkUploadJob, RegistrationBulkUploadRow, RegistrationProvider, RegistrationSchema
from osf.models.registration_bulk_upload_job import JobState
from osf.models.registration_bulk_upload_row import RegistrationBulkUploadContributors
from osf.registrations.utils import get_registration_provider_submissions_url
from osf.utils.permissions import ADMIN, READ, WRITE

from osf_tests.factories import InstitutionFactory, SubjectFactory, UserFactory

from website import mails, settings


class TestRegistrationBulkUploadContributors:

    @pytest.fixture()
    def admin_set(self):
        return {'admin1@email.com', 'admin2@email.com'}

    @pytest.fixture()
    def read_set(self):
        return {'read1@email.com', 'read2@email.com'}

    @pytest.fixture()
    def write_set(self):
        return {'write1@email.com', 'write2@email.com'}

    @pytest.fixture()
    def author_set(self):
        return {'read1@email.com', 'write1@email.com', 'admin1@email.com'}

    @pytest.fixture()
    def contributors(self, admin_set, read_set, write_set, author_set):
        return RegistrationBulkUploadContributors(admin_set, read_set, write_set, author_set, [])

    def test_is_bibliographic(self, admin_set, read_set, write_set, author_set):
        contributors = RegistrationBulkUploadContributors(admin_set, read_set, write_set, author_set, [])
        assert contributors.is_bibliographic('read1@email.com') is True
        assert contributors.is_bibliographic('write2@email.com') is False

    def test_get_permission(self, contributors):
        assert contributors.get_permission('read1@email.com') == READ
        assert contributors.get_permission('write1@email.com') == WRITE
        assert contributors.get_permission('admin1@email.com') == ADMIN
        with pytest.raises(RegistrationBulkCreationContributorError):
            contributors.get_permission('random@email.com')


class TestRegistrationBulkCreationRowError:

    def test_error_message_with_detail(self):
        error = RegistrationBulkCreationRowError('1', '23', 'abc', '45de', error='678fg')
        assert error.short_message == 'Title: abc, External ID: 45de, Error: 678fg'
        assert error.long_message == 'Draft registration creation failed: [upload_id="1", row_id="23", ' \
                                     'title="abc", external_id="45de", error="678fg"]'

    def test_error_message_default(self):
        error = RegistrationBulkCreationRowError('1', '23', 'abc', '45de')
        assert error.short_message == 'Title: abc, External ID: 45de, Error: Draft registration creation error'
        assert error.long_message == 'Draft registration creation failed: [upload_id="1", row_id="23", ' \
                                     'title="abc", external_id="45de", error="Draft registration creation error"]'


@pytest.mark.django_db
class TestBulkUploadTasks:

    @pytest.fixture()
    def initiator(self):
        return UserFactory(username='admin1@email.com', fullname='admin1')

    @pytest.fixture()
    def read_contributor(self):
        return UserFactory(username='read1@email.com', fullname='read1')

    @pytest.fixture()
    def write_contributor(self):
        return UserFactory(username='write1@email.com', fullname='write1')

    @pytest.fixture()
    def schema(self):
        return RegistrationSchema.objects.get(name='Open-Ended Registration', schema_version=3)

    @pytest.fixture()
    def subjects(self):
        return [SubjectFactory() for _ in range(5)]

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def provider(self, schema, subjects):
        provider = RegistrationProvider.load('osf')
        provider.allow_bulk_uploads = True
        provider.schemas.add(schema)
        provider.subjects.add(*subjects)
        provider.save()
        return provider

    @pytest.fixture()
    def upload_job_done_full(self, initiator, provider, schema):
        job = RegistrationBulkUploadJob.create(str(uuid.uuid4()), initiator, provider, schema)
        job.state = JobState.PICKED_UP
        job.save()
        return job

    @pytest.fixture()
    def upload_job_done_partial(self, initiator, provider, schema):
        job = RegistrationBulkUploadJob.create(str(uuid.uuid4()), initiator, provider, schema)
        job.state = JobState.PICKED_UP
        job.save()
        return job

    @pytest.fixture()
    def upload_job_done_error(self, initiator, provider, schema):
        job = RegistrationBulkUploadJob.create(str(uuid.uuid4()), initiator, provider, schema)
        job.state = JobState.PICKED_UP
        job.save()
        return job

    @pytest.fixture()
    def csv_parsed_1(self, subjects):
        return {
            'metadata': {
                'Title': 'Test title 1 & 3',
                'Description': 'Test description 1 & 3',
                'Admin Contributors': [
                    {'full_name': 'admin1', 'email': 'admin1@email.com'},
                    {'full_name': 'admin2', 'email': 'admin2@email.com'},
                ],
                'Read-Write Contributors': [
                    {'full_name': 'write1', 'email': 'write1@email.com'},
                    {'full_name': 'write2', 'email': 'write2@email.com'},
                ],
                'Read-Only Contributors': [
                    {'full_name': 'read1', 'email': 'read1@email.com'},
                    {'full_name': 'read2', 'email': 'read2@email.com'},
                ],
                'Bibliographic Contributors': [
                    {'full_name': 'admin1', 'email': 'admin1@email.com'},
                    {'full_name': 'write1', 'email': 'write1@email.com'},
                    {'full_name': 'read1', 'email': 'read1@email.com'},
                ],
                'Category': 'project',
                'Affiliated Institutions': [],
                'License': {
                    'name': 'No license',
                    'required_fields': {
                        'year': '2030', 'copyright_holders': ['jane doe', 'john doe', 'joan doe']
                    }
                },
                'Subjects': [subject.text for subject in subjects],
                'Tags': [],
                'Project GUID': '',
                'External ID': '1234abcd',
                'summary': 'Test study 1 & 3',
            },
            'registration_responses': {}
        }

    @pytest.fixture()
    def csv_parsed_2(self, subjects):
        return {
            'metadata': {
                'Title': 'Test title 2',
                'Description': 'Test description 2',
                'Admin Contributors': [
                    {'full_name': 'admin1', 'email': 'admin1@email.com'},
                    {'full_name': 'admin3', 'email': 'admin3@email.com'},
                ],
                'Read-Write Contributors': [
                    {'full_name': 'write1', 'email': 'write1@email.com'},
                    {'full_name': 'write3', 'email': 'write3@email.com'},
                ],
                'Read-Only Contributors': [
                    {'full_name': 'read1', 'email': 'read1@email.com'},
                    {'full_name': 'read3', 'email': 'read3@email.com'},
                ],
                'Bibliographic Contributors': [
                    {'full_name': 'admin1', 'email': 'admin1@email.com'},
                    {'full_name': 'write1', 'email': 'write1@email.com'},
                    {'full_name': 'read1', 'email': 'read1@email.com'},
                ],
                'Category': 'project',
                'Affiliated Institutions': [],
                'License': {
                    'name': 'No license',
                    'required_fields': {
                        'year': '2030', 'copyright_holders': ['jane doe', 'john doe', 'joan doe']
                    }
                },
                'Subjects': [subject.text for subject in subjects],
                'Tags': [],
                'Project GUID': '',
                'External ID': '5678efgh',
                'summary': 'Test study 2',
            },
            'registration_responses': {}
        }

    @pytest.fixture()
    def csv_parsed_extra_bib(self, subjects):
        return {
            'metadata': {
                'Title': 'Test title Invalid - Extra Bibliographic Contributor',
                'Description': 'Test description - Extra Bibliographic Contributor',
                'Admin Contributors': [
                    {'full_name': 'admin1', 'email': 'admin1@email.com'},
                ],
                'Read-Write Contributors': [
                    {'full_name': 'write1', 'email': 'write1@email.com'},
                ],
                'Read-Only Contributors': [
                    {'full_name': 'read1', 'email': 'read1@email.com'},
                ],
                'Bibliographic Contributors': [
                    {'full_name': 'admin1', 'email': 'admin1@email.com'},
                    {'full_name': 'write1', 'email': 'write1@email.com'},
                    {'full_name': 'read1', 'email': 'read1@email.com'},
                    {'full_name': 'extra', 'email': 'extra@email.com'},
                ],
                'Category': 'project',
                'Affiliated Institutions': [],
                'License': {
                    'name': 'No license',
                    'required_fields': {
                        'year': '2030', 'copyright_holders': ['jane doe', 'john doe', 'joan doe']
                    }
                },
                'Subjects': [subject.text for subject in subjects],
                'Tags': [],
                'Project GUID': '',
                'External ID': '90-=ijkl',
                'summary': 'Test study Invalid - Extra Bibliographic Contributor',
            },
            'registration_responses': {}
        }

    @pytest.fixture()
    def csv_parsed_invalid_affiliation(self, subjects, institution):
        return {
            'metadata': {
                'Title': 'Test title Invalid - Unauthorized Affiliation',
                'Description': 'Test description - Unauthorized Affiliation',
                'Admin Contributors': [
                    {'full_name': 'admin1', 'email': 'admin1@email.com'},
                ],
                'Read-Write Contributors': [
                    {'full_name': 'write1', 'email': 'write1@email.com'},
                ],
                'Read-Only Contributors': [
                    {'full_name': 'read1', 'email': 'read1@email.com'},
                ],
                'Bibliographic Contributors': [
                    {'full_name': 'admin1', 'email': 'admin1@email.com'},
                    {'full_name': 'write1', 'email': 'write1@email.com'},
                    {'full_name': 'read1', 'email': 'read1@email.com'},
                ],
                'Category': 'project',
                'Affiliated Institutions': [institution.name],
                'License': {
                    'name': 'No license',
                    'required_fields': {
                        'year': '2030', 'copyright_holders': ['jane doe', 'john doe', 'joan doe']
                    }
                },
                'Subjects': [subject.text for subject in subjects],
                'Tags': [],
                'Project GUID': '',
                'External ID': 'mnopqrst',
                'summary': 'Test study Invalid - Unauthorized Affiliation',
            },
            'registration_responses': {}
        }

    @pytest.fixture()
    def registration_row_1(self, upload_job_done_full, csv_parsed_1):
        row = RegistrationBulkUploadRow.create(upload_job_done_full, str(uuid.uuid4()), csv_parsed_1)
        row.save()
        return row

    @pytest.fixture()
    def registration_row_2(self, upload_job_done_full, csv_parsed_2):
        row = RegistrationBulkUploadRow.create(upload_job_done_full, str(uuid.uuid4()), csv_parsed_2)
        row.save()
        return row

    @pytest.fixture()
    def registration_row_3(self, upload_job_done_partial, csv_parsed_1):
        row = RegistrationBulkUploadRow.create(upload_job_done_partial, str(uuid.uuid4()), csv_parsed_1)
        row.save()
        return row

    @pytest.fixture()
    def registration_row_invalid_extra_bib_1(self, upload_job_done_partial, csv_parsed_extra_bib):
        row = RegistrationBulkUploadRow.create(upload_job_done_partial, str(uuid.uuid4()), csv_parsed_extra_bib)
        row.save()
        return row

    @pytest.fixture()
    def registration_row_invalid_extra_bib_2(self, upload_job_done_error, csv_parsed_extra_bib):
        row = RegistrationBulkUploadRow.create(upload_job_done_error, str(uuid.uuid4()), csv_parsed_extra_bib)
        row.save()
        return row

    @pytest.fixture()
    def registration_row_invalid_affiliation(self, upload_job_done_error, csv_parsed_invalid_affiliation):
        row = RegistrationBulkUploadRow.create(upload_job_done_error, str(uuid.uuid4()), csv_parsed_invalid_affiliation)
        row.save()
        return row

    def test_bulk_creation_dry_run(self, registration_row_1, registration_row_2, upload_job_done_full, provider, initiator):
        bulk_create_registrations(upload_job_done_full.id)
        upload_job_done_full.reload()
        assert upload_job_done_full.state == JobState.PICKED_UP
        assert not upload_job_done_full.email_sent

    @mock.patch('website.mails.settings.USE_EMAIL', False)
    @mock.patch('website.mails.send_mail', return_value=None, side_effect=mails.send_mail)
    def test_bulk_creation_done_full(self, mock_send_mail, registration_row_1, registration_row_2,
                                     upload_job_done_full, provider, initiator, read_contributor, write_contributor):

        bulk_create_registrations(upload_job_done_full.id, dry_run=False)
        upload_job_done_full.reload()
        assert upload_job_done_full.state == JobState.DONE_FULL
        assert upload_job_done_full.email_sent
        assert len(RegistrationBulkUploadRow.objects.filter(upload__id=upload_job_done_full.id)) == 2

        for row in [registration_row_1, registration_row_2]:
            row.reload()
            assert row.is_picked_up
            assert row.is_completed
            assert len(row.draft_registration.contributors) == 6
            assert row.draft_registration.contributor_set.get(user=initiator).permission == ADMIN
            assert row.draft_registration.contributor_set.get(user=write_contributor).permission == WRITE
            assert row.draft_registration.contributor_set.get(user=read_contributor).permission == READ

        mock_send_mail.assert_called_with(
            to_addr=initiator.username,
            mail=mails.REGISTRATION_BULK_UPLOAD_SUCCESS_ALL,
            fullname=initiator.fullname,
            auto_approval=False,
            count=2,
            pending_submissions_url=get_registration_provider_submissions_url(provider),
        )

    @mock.patch('website.mails.settings.USE_EMAIL', False)
    @mock.patch('website.mails.send_mail', return_value=None, side_effect=mails.send_mail)
    def test_bulk_creation_done_partial(self, mock_send_mail, registration_row_3,
                                        registration_row_invalid_extra_bib_1, upload_job_done_partial,
                                        provider, initiator, read_contributor, write_contributor):

        bulk_create_registrations(upload_job_done_partial.id, dry_run=False)
        upload_job_done_partial.reload()
        assert upload_job_done_partial.state == JobState.DONE_PARTIAL
        assert upload_job_done_partial.email_sent
        assert len(RegistrationBulkUploadRow.objects.filter(upload__id=upload_job_done_partial.id)) == 1

        registration_row_3.reload()
        assert registration_row_3.is_picked_up
        assert registration_row_3.is_completed
        assert len(registration_row_3.draft_registration.contributors) == 6
        assert registration_row_3.draft_registration.contributor_set.get(user=initiator).permission == ADMIN
        assert registration_row_3.draft_registration.contributor_set.get(user=write_contributor).permission == WRITE
        assert registration_row_3.draft_registration.contributor_set.get(user=read_contributor).permission == READ

        mock_send_mail.assert_called_with(
            to_addr=initiator.username,
            mail=mails.REGISTRATION_BULK_UPLOAD_SUCCESS_PARTIAL,
            fullname=initiator.fullname,
            auto_approval=False,
            approval_errors=[],
            draft_errors=[
                'Title: Test title Invalid - Extra Bibliographic Contributor, External ID: 90-=ijkl, '
                'Error: Bibliographic contributors must be one of admin, read-only or read-write'
            ],
            total=2,
            successes=1,
            failures=1,
            pending_submissions_url=get_registration_provider_submissions_url(provider),
            osf_support_email=settings.OSF_SUPPORT_EMAIL,
        )

    @mock.patch('website.mails.settings.USE_EMAIL', False)
    @mock.patch('website.mails.send_mail', return_value=None, side_effect=mails.send_mail)
    def test_bulk_creation_done_error(self, mock_send_mail, registration_row_invalid_extra_bib_2,
                                      registration_row_invalid_affiliation, upload_job_done_error,
                                      provider, initiator, read_contributor, write_contributor, institution):

        bulk_create_registrations(upload_job_done_error.id, dry_run=False)
        upload_job_done_error.reload()
        assert upload_job_done_error.state == JobState.DONE_ERROR
        assert upload_job_done_error.email_sent
        assert len(RegistrationBulkUploadRow.objects.filter(upload__id=upload_job_done_error.id)) == 0

        mock_send_mail.assert_called_with(
            to_addr=initiator.username,
            mail=mails.REGISTRATION_BULK_UPLOAD_FAILURE_ALL,
            fullname=initiator.fullname,
            draft_errors=[
                'Title: Test title Invalid - Extra Bibliographic Contributor, External ID: 90-=ijkl, '
                'Error: Bibliographic contributors must be one of admin, read-only or read-write',
                f'Title: Test title Invalid - Unauthorized Affiliation, External ID: mnopqrst, '
                f'Error: Initiator [{initiator._id}] is not affiliated with institution [{institution._id}]',
            ],
            count=2,
            osf_support_email=settings.OSF_SUPPORT_EMAIL,
        )
