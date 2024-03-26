from faker import Faker
import pytest

from api_tests.utils import create_test_file

from osf.models import CedarMetadataRecord, CedarMetadataTemplate
from osf_tests.factories import AuthUserFactory, ProjectFactory, RegistrationFactory

fake = Faker()


@pytest.mark.django_db
class TestCedarMetadataRecord:

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
    def node_alt(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def node_pub(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture()
    def node_pub_alt(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture()
    def registration(self, user):
        return RegistrationFactory(creator=user, is_public=True)

    @pytest.fixture()
    def registration_alt(self, user):
        return RegistrationFactory(creator=user, is_public=True)

    @pytest.fixture()
    def file(self, user, node):
        return create_test_file(node, user, create_guid=True)

    @pytest.fixture()
    def file_alt(self, user, node_alt):
        return create_test_file(node_alt, user, create_guid=True)

    @pytest.fixture()
    def file_pub(self, user, node_pub):
        return create_test_file(node_pub, user, create_guid=True)

    @pytest.fixture()
    def file_pub_alt(self, user, node_pub_alt):
        return create_test_file(node_pub_alt, user, create_guid=True)

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
    def cedar_template_alt(self, cedar_template_json):
        return CedarMetadataTemplate.objects.create(
            schema_name=fake.bs(),
            cedar_id=fake.md5(),
            template_version=1,
            template=cedar_template_json,
            active=True,
        )

    @pytest.fixture()
    def cedar_template_inactive(self, cedar_template_json):
        return CedarMetadataTemplate.objects.create(
            schema_name=fake.bs(),
            cedar_id=fake.md5(),
            template_version=1,
            template=cedar_template_json,
            active=False,
        )

    @pytest.fixture()
    def cedar_record_metadata_json(self):
        return {'rm_key_1': 'rm_value_1', 'rm_key_2': 'rm_value_2', 'rm_key_3': 'rm_value_3'}

    @pytest.fixture()
    def cedar_record_metadata_alt_json(self):
        return {'rm_key_2': 'rm_value_2', 'rm_key_3': 'rm_value_3', 'rm_key_4': 'rm_value_4'}

    @pytest.fixture()
    def cedar_record_for_node(self, node, cedar_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=node.guids.first(),
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )

    @pytest.fixture()
    def cedar_draft_record_for_node_alt(self, node_alt, cedar_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=node_alt.guids.first(),
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=False,
        )

    @pytest.fixture()
    def cedar_record_for_node_pub(self, node_pub, cedar_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=node_pub.guids.first(),
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )

    @pytest.fixture()
    def cedar_draft_record_for_node_pub_alt(self, node_pub_alt, cedar_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=node_pub_alt.guids.first(),
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=False,
        )

    @pytest.fixture()
    def cedar_record_for_registration(self, registration, cedar_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=registration.guids.first(),
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )

    @pytest.fixture()
    def cedar_draft_record_for_registration_alt(self, registration_alt, cedar_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=registration_alt.guids.first(),
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=False,
        )

    @pytest.fixture()
    def cedar_record_for_file(self, file, cedar_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=file.get_guid(create=False),
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )

    @pytest.fixture()
    def cedar_draft_record_for_file_alt(self, file_alt, cedar_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=file_alt.get_guid(create=False),
            template=cedar_template,
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
    def cedar_draft_record_for_file_pub_alt(self, file_pub_alt, cedar_template, cedar_record_metadata_json):
        return CedarMetadataRecord.objects.create(
            guid=file_pub_alt.get_guid(create=False),
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=False,
        )

    @pytest.fixture()
    def cedar_draft_record_ids(self, cedar_draft_record_for_node_alt, cedar_draft_record_for_node_pub_alt, cedar_draft_record_for_registration_alt, cedar_draft_record_for_file_alt, cedar_draft_record_for_file_pub_alt):
        return [cedar_draft_record_for_node_alt._id, cedar_draft_record_for_node_pub_alt._id, cedar_draft_record_for_registration_alt._id, cedar_draft_record_for_file_alt._id, cedar_draft_record_for_file_pub_alt._id]

    @pytest.fixture()
    def cedar_published_private_record_ids(self, cedar_record_for_node, cedar_record_for_file):
        return [cedar_record_for_node._id, cedar_record_for_file._id]

    @pytest.fixture()
    def cedar_published_public_record_ids(self, cedar_record_for_node_pub, cedar_record_for_registration, cedar_record_for_file_pub):
        return [cedar_record_for_node_pub._id, cedar_record_for_registration._id, cedar_record_for_file_pub._id]

    @pytest.fixture()
    def all_cedar_record_ids(self, cedar_draft_record_ids, cedar_published_private_record_ids, cedar_published_public_record_ids):
        return cedar_draft_record_ids + cedar_published_private_record_ids + cedar_published_public_record_ids

    @pytest.fixture
    def payload_node(self, cedar_template_alt, cedar_record_metadata_json, node):

        return {
            'data': {
                'type': 'cedar_metadata_records',
                'attributes': {
                    'metadata': cedar_record_metadata_json,
                    'is_published': 'true'
                },
                'relationships': {
                    'template': {
                        'data': {
                            'type': 'cedar-metadata-templates',
                            'id': cedar_template_alt._id
                        }
                    },
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': node._id
                        }
                    }
                }
            }
        }

    @pytest.fixture
    def payload_registration(self, cedar_template_alt, cedar_record_metadata_json, registration):

        return {
            'data': {
                'type': 'cedar_metadata_records',
                'attributes': {
                    'metadata': cedar_record_metadata_json,
                    'is_published': 'true'
                },
                'relationships': {
                    'template': {
                        'data': {
                            'type': 'cedar-metadata-templates',
                            'id': cedar_template_alt._id
                        }
                    },
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': registration._id
                        }
                    }
                }
            }
        }

    @pytest.fixture
    def payload_file(self, cedar_template_alt, cedar_record_metadata_json, file):

        return {
            'data': {
                'type': 'cedar_metadata_records',
                'attributes': {
                    'metadata': cedar_record_metadata_json,
                    'is_published': 'true'
                },
                'relationships': {
                    'template': {
                        'data': {
                            'type': 'cedar-metadata-templates',
                            'id': cedar_template_alt._id
                        }
                    },
                    'target': {
                        'data': {
                            'type': 'files',
                            'id': file.get_guid()._id
                        }
                    }
                }
            }
        }

    @pytest.fixture()
    def payload_record_update(self, cedar_record_metadata_alt_json):

        return {
            'data': {
                'type': 'cedar_metadata_records',
                'attributes': {
                    'metadata': cedar_record_metadata_alt_json,
                    'is_published': 'false'
                }
            }
        }

    @staticmethod
    def get_record_metadata_download_file_name(record):
        return f'{record._id}-{record.get_template_name()}-v{record.get_template_version()}.json'
