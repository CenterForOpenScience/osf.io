import pytest
from urllib.parse import urlparse

from .test_template import TestCedarMetadataTemplate

from api.base.settings import API_PRIVATE_BASE


@pytest.mark.django_db
class TestCedarMetadataTemplateDetail(TestCedarMetadataTemplate):
    def test_template_detail_active(self, app, active_template):
        resp = app.get(f"/_/cedar_metadata_templates/{active_template._id}/")
        assert resp.status_code == 200
        data = resp.json["data"]
        assert data["id"] == active_template._id
        assert data["type"] == "cedar-metadata-templates"
        assert data["attributes"]["schema_name"] == active_template.schema_name
        assert data["attributes"]["cedar_id"] == active_template.cedar_id
        assert data["attributes"]["template"] == active_template.template
        assert data["attributes"]["active"] is True
        assert (
            data["attributes"]["template_version"]
            == active_template.template_version
        )
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{active_template._id}/"
        )

    def test_template_detail_inactive(self, app, inactive_template):
        resp = app.get(f"/_/cedar_metadata_templates/{inactive_template._id}/")
        assert resp.status_code == 200
        data = resp.json["data"]
        assert data["id"] == inactive_template._id
        assert data["type"] == "cedar-metadata-templates"
        assert (
            data["attributes"]["schema_name"] == inactive_template.schema_name
        )
        assert data["attributes"]["cedar_id"] == inactive_template.cedar_id
        assert data["attributes"]["template"] == inactive_template.template
        assert data["attributes"]["active"] is False
        assert (
            data["attributes"]["template_version"]
            == inactive_template.template_version
        )
        assert (
            urlparse(data["links"]["self"]).path
            == f"/{API_PRIVATE_BASE}cedar_metadata_templates/{inactive_template._id}/"
        )

    def test_template_detail_not_found(self, app, invalid_template_id):
        resp = app.get(
            f"/_/cedar_metadata_templates/{invalid_template_id}/",
            expect_errors=True,
        )
        assert resp.status_code == 404
