import pytest

from .test_template import TestCedarMetadataTemplate


@pytest.mark.django_db
class TestCedarMetadataTemplateList(TestCedarMetadataTemplate):

    def test_template_list(self, app, active_template_ids):

        resp = app.get('/_/cedar_metadata_templates/')
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 2
        assert set(active_template_ids) == {datum['id'] for datum in data}
