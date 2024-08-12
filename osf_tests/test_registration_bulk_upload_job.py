import uuid
import pytest

from django.db.utils import IntegrityError

from osf.models import RegistrationBulkUploadJob
from osf.models.registration_bulk_upload_job import JobState
from osf_tests.factories import (
    UserFactory,
    RegistrationProviderFactory,
    get_default_metaschema,
)


@pytest.mark.django_db
class TestRegistrationBulkUploadJob:
    @pytest.fixture()
    def payload_hash(self):
        return str(uuid.uuid4()).replace("-", "")

    @pytest.fixture()
    def initiator(self):
        return UserFactory()

    @pytest.fixture()
    def schema(self):
        return get_default_metaschema()

    @pytest.fixture()
    def provider(self):
        return RegistrationProviderFactory()

    def test_job_creation(self, payload_hash, initiator, provider, schema):
        upload_job = RegistrationBulkUploadJob.create(
            payload_hash, initiator, provider, schema
        )
        upload_job.save()
        upload_job.reload()
        assert upload_job.payload_hash == payload_hash
        assert upload_job.initiator == initiator
        assert upload_job.schema == schema
        assert upload_job.provider == provider
        assert upload_job.state == JobState.PENDING
        assert upload_job.email_sent is None

    def test_job_uniqueness(self, payload_hash, initiator, provider, schema):
        upload_job_1 = RegistrationBulkUploadJob.create(
            payload_hash, initiator, provider, schema
        )
        upload_job_1.save()
        upload_job_2 = RegistrationBulkUploadJob.create(
            payload_hash, initiator, provider, schema
        )
        with pytest.raises(IntegrityError):
            upload_job_2.save()
