from faker import Faker
import pytest

from api_tests.utils import create_test_file

from osf.models import CedarMetadataRecord, CedarMetadataTemplate
from osf_tests.factories import AuthUserFactory, ProjectFactory

fake = Faker()


@pytest.mark.django_db
class TestFileCedarMetadataRecord:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_alt(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def node_pub(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture()
    def file(self, user, node):
        return create_test_file(node, user, create_guid=True)

    @pytest.fixture()
    def file_pub(self, user, node_pub):
        return create_test_file(node_pub, user, create_guid=True)

    @pytest.fixture()
    def cedar_template_json(self):
        return {'t_key_1': 't_value_1', 't_key_2': 't_value_2', 't_key_3': 't_value_3'}

    @pytest.fixture()
    def cedar_template(self, cedar_template_json):
        return CedarMetadataTemplate.objects.create(
            schema_name=fake.bs(),
            cedar_id=fake.md5(),
            template_version=1,
            template=cedar_template_json,
            active=True,
        )

    @pytest.fixture()
    def cedar_draft_template(self, cedar_template_json):
        return CedarMetadataTemplate.objects.create(
            schema_name=fake.bs(),
            cedar_id=fake.md5(),
            template_version=1,
            template=cedar_template_json,
            active=True,
        )

    @pytest.fixture()
    def cedar_record_metadata_json(self):
        return {'rm_key_1': 'rm_value_1', 'rm_key_2': 'rm_value_2', 'rm_key_3': 'rm_value_3'}

    @pytest.fixture()
    def cedar_record_for_file(self, file, cedar_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=file.get_guid(create=False),
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )

    @pytest.fixture()
    def cedar_draft_record_for_file(self, file, cedar_draft_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=file.get_guid(create=False),
            template=cedar_draft_template,
            metadata=cedar_record_metadata_json,
            is_published=False,
        )

    @pytest.fixture()
    def cedar_record_for_file_pub(self, file_pub, cedar_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=file_pub.get_guid(create=False),
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )

    @pytest.fixture()
    def cedar_draft_record_for_file_pub(self, file_pub, cedar_draft_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=file_pub.get_guid(create=False),
            template=cedar_draft_template,
            metadata=cedar_record_metadata_json,
            is_published=False,
        )
