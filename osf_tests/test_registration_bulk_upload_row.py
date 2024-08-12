import hashlib
import pytest

from django.db.utils import IntegrityError

from api.base.settings import BULK_SETTINGS

from osf.models import RegistrationBulkUploadRow
from osf_tests.factories import RegistrationBulkUploadJobFactory
from osf.utils.fields import ensure_bytes


@pytest.mark.django_db
class TestRegistrationBulkUploadRow:
    @pytest.fixture()
    def upload_job(self):
        return RegistrationBulkUploadJobFactory()

    @pytest.fixture()
    def csv_raw_1(self):
        return "a" * BULK_SETTINGS["DEFAULT_BULK_LIMIT"] * 1

    @pytest.fixture()
    def csv_raw_2(self):
        return "b" * BULK_SETTINGS["DEFAULT_BULK_LIMIT"] * 1

    @pytest.fixture()
    def row_hash_1(self, csv_raw_1):
        return hashlib.md5(ensure_bytes(csv_raw_1)).hexdigest()

    @pytest.fixture()
    def row_hash_2(self, csv_raw_2):
        return hashlib.md5(ensure_bytes(csv_raw_2)).hexdigest()

    @pytest.fixture()
    def csv_parsed_1(self):
        return {"key_1": "val_1", "key_2": "val_2"}

    @pytest.fixture()
    def csv_parsed_2(self):
        return {"key_2": "val_2", "key_3": "val_3"}

    def test_row_creation(
        self, upload_job, csv_raw_1, csv_parsed_1, row_hash_1
    ):
        registration_row = RegistrationBulkUploadRow.create(
            upload_job, csv_raw_1, csv_parsed_1
        )
        registration_row.save()
        registration_row.reload()
        assert registration_row.draft_registration is None
        assert registration_row.is_completed is False
        assert registration_row.is_picked_up is False
        assert registration_row.row_hash == row_hash_1
        assert registration_row.upload == upload_job
        assert registration_row.csv_raw == csv_raw_1
        assert registration_row.csv_parsed == csv_parsed_1

    def test_row_object_hash(
        self, upload_job, csv_raw_2, csv_parsed_2, row_hash_2
    ):
        registration_row = RegistrationBulkUploadRow.create(
            upload_job, csv_raw_2, csv_parsed_2
        )
        assert registration_row.__hash__() == hash(row_hash_2)
        registration_row.save()
        registration_row.reload()
        assert registration_row.__hash__() == hash(registration_row.pk)

    def test_row_object_eq(
        self, upload_job, csv_raw_1, csv_raw_2, csv_parsed_1, csv_parsed_2
    ):
        registration_row_1 = RegistrationBulkUploadRow.create(
            upload_job, csv_raw_1, csv_parsed_1
        )
        registration_row_2 = RegistrationBulkUploadRow.create(
            upload_job, csv_raw_2, csv_parsed_2
        )
        registration_row_3 = RegistrationBulkUploadRow.create(
            upload_job, csv_raw_2, csv_parsed_2
        )
        assert registration_row_1 != registration_row_2
        assert registration_row_2 == registration_row_3

    def test_row_uniqueness(
        self, upload_job, csv_raw_1, csv_raw_2, csv_parsed_1, csv_parsed_2
    ):
        registration_row_1 = RegistrationBulkUploadRow.create(
            upload_job, csv_raw_1, csv_parsed_1
        )
        registration_row_1.save()
        registration_row_2 = RegistrationBulkUploadRow.create(
            upload_job, csv_raw_1, csv_parsed_2
        )
        with pytest.raises(IntegrityError):
            registration_row_2.save()
