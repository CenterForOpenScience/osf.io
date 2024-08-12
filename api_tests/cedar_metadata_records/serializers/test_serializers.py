import pytest
from urllib.parse import urlparse

from api.base.settings.defaults import API_BASE, API_PRIVATE_BASE
from api.cedar_metadata_records.serializers import (
    CedarMetadataRecordsBaseSerializer,
    CedarMetadataRecordsListSerializer,
    CedarMetadataRecordsCreateSerializer,
    CedarMetadataRecordsDetailSerializer,
)
from api_tests.utils import create_test_file
from osf.models import CedarMetadataRecord, CedarMetadataTemplate
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
)
from tests.utils import make_drf_request_with_version


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def node(user):
    return ProjectFactory(creator=user)


@pytest.fixture()
def registration(user):
    return RegistrationFactory(creator=user)


@pytest.fixture()
def file(user, node):
    return create_test_file(node, user, create_guid=True)


@pytest.fixture()
def cedar_template_json():
    return {
        "t_key_1": "t_value_1",
        "t_key_2": "t_value_2",
        "t_key_3": "t_value_3",
    }


@pytest.fixture()
def cedar_template(cedar_template_json):
    return CedarMetadataTemplate.objects.create(
        schema_name="cedar_test_schema_name",
        cedar_id="cedar_test_id",
        template_version=1,
        template=cedar_template_json,
        active=True,
    )


@pytest.fixture()
def cedar_record_metadata_json():
    return {
        "rm_key_1": "rm_value_1",
        "rm_key_2": "rm_value_2",
        "rm_key_3": "rm_value_3",
    }


@pytest.mark.django_db
class TestCedarMetadataRecordsBaseSerializer:
    def test_serializer_when_target_is_node(
        self, node, cedar_template, cedar_record_metadata_json
    ):
        guid = node.guids.first()
        cedar_record = CedarMetadataRecord.objects.create(
            guid=guid,
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )
        context = {"request": make_drf_request_with_version()}
        data = CedarMetadataRecordsBaseSerializer(
            cedar_record, context=context
        ).data["data"]
        assert data["id"] == cedar_record._id
        assert data["type"] == "cedar-metadata-records"

        # Attributes
        assert data["attributes"]["metadata"] == cedar_record_metadata_json
        assert data["attributes"]["is_published"] is True

        # Relationships
        assert data["relationships"]["target"]["data"] == {
            "id": node._id,
            "type": "nodes",
        }
        assert (
            urlparse(
                data["relationships"]["target"]["links"]["related"]["href"]
            ).path
            == f"/{API_BASE}nodes/{node._id}/"
        )
        assert data["relationships"]["template"]["data"] == {
            "id": cedar_template._id,
            "type": "cedar-metadata-templates",
        }
        assert (
            urlparse(
                data["relationships"]["template"]["links"]["related"]["href"]
            ).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/"
        )

        # Links
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/"
        )
        assert (
            urlparse(data["links"]["metadata_download"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/metadata_download/"
        )

    def test_serializer_when_target_is_registration(
        self, registration, cedar_template, cedar_record_metadata_json
    ):
        guid = registration.guids.first()
        cedar_record = CedarMetadataRecord.objects.create(
            guid=guid,
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )
        context = {"request": make_drf_request_with_version()}
        data = CedarMetadataRecordsBaseSerializer(
            cedar_record, context=context
        ).data["data"]
        assert data["id"] == cedar_record._id
        assert data["type"] == "cedar-metadata-records"

        # Attributes
        assert data["attributes"]["metadata"] == cedar_record_metadata_json
        assert data["attributes"]["is_published"] is True

        # Relationships
        assert data["relationships"]["target"]["data"] == {
            "id": registration._id,
            "type": "registrations",
        }
        assert (
            urlparse(
                data["relationships"]["target"]["links"]["related"]["href"]
            ).path
            == f"/{API_BASE}registrations/{registration._id}/"
        )
        assert data["relationships"]["template"]["data"] == {
            "id": cedar_template._id,
            "type": "cedar-metadata-templates",
        }
        assert (
            urlparse(
                data["relationships"]["template"]["links"]["related"]["href"]
            ).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/"
        )

        # Links
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/"
        )
        assert (
            urlparse(data["links"]["metadata_download"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/metadata_download/"
        )

    def test_serializer_when_target_is_file(
        self, file, cedar_template, cedar_record_metadata_json
    ):
        guid = file.get_guid(create=False)
        cedar_record = CedarMetadataRecord.objects.create(
            guid=guid,
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )
        context = {"request": make_drf_request_with_version()}
        data = CedarMetadataRecordsBaseSerializer(
            cedar_record, context=context
        ).data["data"]
        assert data["id"] == cedar_record._id
        assert data["type"] == "cedar-metadata-records"

        # Attributes
        assert data["attributes"]["metadata"] == cedar_record_metadata_json
        assert data["attributes"]["is_published"] is True

        # Relationships
        assert data["relationships"]["target"]["data"] == {
            "id": guid._id,
            "type": "files",
        }
        assert (
            urlparse(
                data["relationships"]["target"]["links"]["related"]["href"]
            ).path
            == f"/{API_BASE}files/{guid._id}/"
        )
        assert data["relationships"]["template"]["data"] == {
            "id": cedar_template._id,
            "type": "cedar-metadata-templates",
        }
        assert (
            urlparse(
                data["relationships"]["template"]["links"]["related"]["href"]
            ).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/"
        )

        # Links
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/"
        )
        assert (
            urlparse(data["links"]["metadata_download"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/metadata_download/"
        )


@pytest.mark.django_db
class TestCedarMetadataRecordsListSerializer:
    def test_serializer_when_target_is_node(
        self, node, cedar_template, cedar_record_metadata_json
    ):
        guid = node.guids.first()
        cedar_record = CedarMetadataRecord.objects.create(
            guid=guid,
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )
        context = {"request": make_drf_request_with_version()}
        data = CedarMetadataRecordsCreateSerializer(
            cedar_record, context=context
        ).data["data"]
        assert data["id"] == cedar_record._id
        assert data["type"] == "cedar-metadata-records"

        # Attributes
        assert data["attributes"]["metadata"] == cedar_record_metadata_json
        assert data["attributes"]["is_published"] is True

        # Relationships
        assert data["relationships"]["target"]["data"] == {
            "id": node._id,
            "type": "nodes",
        }
        assert (
            urlparse(
                data["relationships"]["target"]["links"]["related"]["href"]
            ).path
            == f"/{API_BASE}nodes/{node._id}/"
        )
        assert data["relationships"]["template"]["data"] == {
            "id": cedar_template._id,
            "type": "cedar-metadata-templates",
        }
        assert (
            urlparse(
                data["relationships"]["template"]["links"]["related"]["href"]
            ).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/"
        )

        # Links
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/"
        )
        assert (
            urlparse(data["links"]["metadata_download"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/metadata_download/"
        )

    def test_serializer_when_target_is_registration(
        self, registration, cedar_template, cedar_record_metadata_json
    ):
        guid = registration.guids.first()
        cedar_record = CedarMetadataRecord.objects.create(
            guid=guid,
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )
        context = {"request": make_drf_request_with_version()}
        data = CedarMetadataRecordsCreateSerializer(
            cedar_record, context=context
        ).data["data"]
        assert data["id"] == cedar_record._id
        assert data["type"] == "cedar-metadata-records"

        # Attributes
        assert data["attributes"]["metadata"] == cedar_record_metadata_json
        assert data["attributes"]["is_published"] is True

        # Relationships
        assert data["relationships"]["target"]["data"] == {
            "id": registration._id,
            "type": "registrations",
        }
        assert (
            urlparse(
                data["relationships"]["target"]["links"]["related"]["href"]
            ).path
            == f"/{API_BASE}registrations/{registration._id}/"
        )
        assert data["relationships"]["template"]["data"] == {
            "id": cedar_template._id,
            "type": "cedar-metadata-templates",
        }
        assert (
            urlparse(
                data["relationships"]["template"]["links"]["related"]["href"]
            ).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/"
        )

        # Links
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/"
        )
        assert (
            urlparse(data["links"]["metadata_download"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/metadata_download/"
        )

    def test_serializer_when_target_is_file(
        self, file, cedar_template, cedar_record_metadata_json
    ):
        guid = file.get_guid(create=False)
        cedar_record = CedarMetadataRecord.objects.create(
            guid=guid,
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )
        context = {"request": make_drf_request_with_version()}
        data = CedarMetadataRecordsCreateSerializer(
            cedar_record, context=context
        ).data["data"]
        assert data["id"] == cedar_record._id
        assert data["type"] == "cedar-metadata-records"

        # Attributes
        assert data["attributes"]["metadata"] == cedar_record_metadata_json
        assert data["attributes"]["is_published"] is True

        # Relationships
        assert data["relationships"]["target"]["data"] == {
            "id": guid._id,
            "type": "files",
        }
        assert (
            urlparse(
                data["relationships"]["target"]["links"]["related"]["href"]
            ).path
            == f"/{API_BASE}files/{guid._id}/"
        )
        assert data["relationships"]["template"]["data"] == {
            "id": cedar_template._id,
            "type": "cedar-metadata-templates",
        }
        assert (
            urlparse(
                data["relationships"]["template"]["links"]["related"]["href"]
            ).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/"
        )

        # Links
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/"
        )
        assert (
            urlparse(data["links"]["metadata_download"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/metadata_download/"
        )


@pytest.mark.django_db
class TestCedarMetadataRecordsCreateSerializer:
    def test_serializer_when_target_is_node(
        self, node, cedar_template, cedar_record_metadata_json
    ):
        guid = node.guids.first()
        cedar_record = CedarMetadataRecord.objects.create(
            guid=guid,
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )
        context = {"request": make_drf_request_with_version()}
        data = CedarMetadataRecordsListSerializer(
            cedar_record, context=context
        ).data["data"]
        assert data["id"] == cedar_record._id
        assert data["type"] == "cedar-metadata-records"

        # Attributes
        assert data["attributes"]["metadata"] == cedar_record_metadata_json
        assert data["attributes"]["is_published"] is True

        # Relationships
        assert data["relationships"]["target"]["data"] == {
            "id": node._id,
            "type": "nodes",
        }
        assert (
            urlparse(
                data["relationships"]["target"]["links"]["related"]["href"]
            ).path
            == f"/{API_BASE}nodes/{node._id}/"
        )
        assert data["relationships"]["template"]["data"] == {
            "id": cedar_template._id,
            "type": "cedar-metadata-templates",
        }
        assert (
            urlparse(
                data["relationships"]["template"]["links"]["related"]["href"]
            ).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/"
        )

        # Links
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/"
        )
        assert (
            urlparse(data["links"]["metadata_download"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/metadata_download/"
        )

    def test_serializer_when_target_is_registration(
        self, registration, cedar_template, cedar_record_metadata_json
    ):
        guid = registration.guids.first()
        cedar_record = CedarMetadataRecord.objects.create(
            guid=guid,
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )
        context = {"request": make_drf_request_with_version()}
        data = CedarMetadataRecordsListSerializer(
            cedar_record, context=context
        ).data["data"]
        assert data["id"] == cedar_record._id
        assert data["type"] == "cedar-metadata-records"

        # Attributes
        assert data["attributes"]["metadata"] == cedar_record_metadata_json
        assert data["attributes"]["is_published"] is True

        # Relationships
        assert data["relationships"]["target"]["data"] == {
            "id": registration._id,
            "type": "registrations",
        }
        assert (
            urlparse(
                data["relationships"]["target"]["links"]["related"]["href"]
            ).path
            == f"/{API_BASE}registrations/{registration._id}/"
        )
        assert data["relationships"]["template"]["data"] == {
            "id": cedar_template._id,
            "type": "cedar-metadata-templates",
        }
        assert (
            urlparse(
                data["relationships"]["template"]["links"]["related"]["href"]
            ).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/"
        )

        # Links
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/"
        )
        assert (
            urlparse(data["links"]["metadata_download"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/metadata_download/"
        )

    def test_serializer_when_target_is_file(
        self, file, cedar_template, cedar_record_metadata_json
    ):
        guid = file.get_guid(create=False)
        cedar_record = CedarMetadataRecord.objects.create(
            guid=guid,
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )
        context = {"request": make_drf_request_with_version()}
        data = CedarMetadataRecordsListSerializer(
            cedar_record, context=context
        ).data["data"]
        assert data["id"] == cedar_record._id
        assert data["type"] == "cedar-metadata-records"

        # Attributes
        assert data["attributes"]["metadata"] == cedar_record_metadata_json
        assert data["attributes"]["is_published"] is True

        # Relationships
        assert data["relationships"]["target"]["data"] == {
            "id": guid._id,
            "type": "files",
        }
        assert (
            urlparse(
                data["relationships"]["target"]["links"]["related"]["href"]
            ).path
            == f"/{API_BASE}files/{guid._id}/"
        )
        assert data["relationships"]["template"]["data"] == {
            "id": cedar_template._id,
            "type": "cedar-metadata-templates",
        }
        assert (
            urlparse(
                data["relationships"]["template"]["links"]["related"]["href"]
            ).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/"
        )

        # Links
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/"
        )
        assert (
            urlparse(data["links"]["metadata_download"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/metadata_download/"
        )


@pytest.mark.django_db
class TestCedarMetadataRecordsDetailSerializer:
    def test_serializer_when_target_is_node(
        self, node, cedar_template, cedar_record_metadata_json
    ):
        guid = node.guids.first()
        cedar_record = CedarMetadataRecord.objects.create(
            guid=guid,
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )
        context = {"request": make_drf_request_with_version()}
        data = CedarMetadataRecordsDetailSerializer(
            cedar_record, context=context
        ).data["data"]
        assert data["id"] == cedar_record._id
        assert data["type"] == "cedar-metadata-records"

        # Attributes
        assert data["attributes"]["metadata"] == cedar_record_metadata_json
        assert data["attributes"]["is_published"] is True

        # Relationships
        assert data["relationships"]["target"]["data"] == {
            "id": node._id,
            "type": "nodes",
        }
        assert (
            urlparse(
                data["relationships"]["target"]["links"]["related"]["href"]
            ).path
            == f"/{API_BASE}nodes/{node._id}/"
        )
        assert data["relationships"]["template"]["data"] == {
            "id": cedar_template._id,
            "type": "cedar-metadata-templates",
        }
        assert (
            urlparse(
                data["relationships"]["template"]["links"]["related"]["href"]
            ).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/"
        )

        # Links
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/"
        )
        assert (
            urlparse(data["links"]["metadata_download"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/metadata_download/"
        )

    def test_serializer_when_target_is_registration(
        self, registration, cedar_template, cedar_record_metadata_json
    ):
        guid = registration.guids.first()
        cedar_record = CedarMetadataRecord.objects.create(
            guid=guid,
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )
        context = {"request": make_drf_request_with_version()}
        data = CedarMetadataRecordsDetailSerializer(
            cedar_record, context=context
        ).data["data"]
        assert data["id"] == cedar_record._id
        assert data["type"] == "cedar-metadata-records"

        # Attributes
        assert data["attributes"]["metadata"] == cedar_record_metadata_json
        assert data["attributes"]["is_published"] is True

        # Relationships
        assert data["relationships"]["target"]["data"] == {
            "id": registration._id,
            "type": "registrations",
        }
        assert (
            urlparse(
                data["relationships"]["target"]["links"]["related"]["href"]
            ).path
            == f"/{API_BASE}registrations/{registration._id}/"
        )
        assert data["relationships"]["template"]["data"] == {
            "id": cedar_template._id,
            "type": "cedar-metadata-templates",
        }
        assert (
            urlparse(
                data["relationships"]["template"]["links"]["related"]["href"]
            ).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/"
        )

        # Links
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/"
        )
        assert (
            urlparse(data["links"]["metadata_download"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/metadata_download/"
        )

    def test_serializer_when_target_is_file(
        self, file, cedar_template, cedar_record_metadata_json
    ):
        guid = file.get_guid(create=False)
        cedar_record = CedarMetadataRecord.objects.create(
            guid=guid,
            template=cedar_template,
            metadata=cedar_record_metadata_json,
            is_published=True,
        )
        context = {"request": make_drf_request_with_version()}
        data = CedarMetadataRecordsDetailSerializer(
            cedar_record, context=context
        ).data["data"]
        assert data["id"] == cedar_record._id
        assert data["type"] == "cedar-metadata-records"

        # Attributes
        assert data["attributes"]["metadata"] == cedar_record_metadata_json
        assert data["attributes"]["is_published"] is True

        # Relationships
        assert data["relationships"]["target"]["data"] == {
            "id": guid._id,
            "type": "files",
        }
        assert (
            urlparse(
                data["relationships"]["target"]["links"]["related"]["href"]
            ).path
            == f"/{API_BASE}files/{guid._id}/"
        )
        assert data["relationships"]["template"]["data"] == {
            "id": cedar_template._id,
            "type": "cedar-metadata-templates",
        }
        assert (
            urlparse(
                data["relationships"]["template"]["links"]["related"]["href"]
            ).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{cedar_template._id}/"
        )

        # Links
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/"
        )
        assert (
            urlparse(data["links"]["metadata_download"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_records/{cedar_record._id}/metadata_download/"
        )
