from faker import Faker
import pytest

from osf.models import CedarMetadataTemplate

fake = Faker()


@pytest.mark.django_db
class TestCedarMetadataTemplate:

    @pytest.fixture()
    def active_template(self):
        return CedarMetadataTemplate.objects.create(
            schema_name=fake.bs(),
            cedar_id=fake.md5(),
            template_version=1,
            template={},
            active=True,
        )

    @pytest.fixture()
    def active_template_alt(self):
        return CedarMetadataTemplate.objects.create(
            schema_name=fake.bs(),
            cedar_id=fake.md5(),
            template_version=1,
            template={},
            active=True,
        )

    @pytest.fixture()
    def active_template_ids(self, active_template, active_template_alt):
        return [active_template._id, active_template_alt._id]

    @pytest.fixture()
    def inactive_template(self):
        return CedarMetadataTemplate.objects.create(
            schema_name=fake.bs(),
            cedar_id=fake.md5(),
            template_version=1,
            template={},
            active=False,
        )

    @pytest.fixture()
    def invalid_template_id(self):
        return fake.md5()
