import pytest

from .test_template import TestCedarMetadataTemplate


@pytest.mark.django_db
class TestCedarMetadataTemplateList(TestCedarMetadataTemplate):

    def test_template_list(self, app, active_template_ids):

        resp = app.get('/_/cedar_metadata_templates/')
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 3
        assert set(active_template_ids) == {datum['id'] for datum in data}

    def test_filter_templates_for_collections_only(self, app, active_template_for_collections, active_template_ids):
        resp = app.get('/_/cedar_metadata_templates/?filter[is_for_collections]=true')
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 1
        assert data[0]['id'] == active_template_for_collections._id

        resp = app.get('/_/cedar_metadata_templates/?filter[is_for_collections]=false')
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 2
        for template in data:
            assert template['id'] != active_template_for_collections._id
