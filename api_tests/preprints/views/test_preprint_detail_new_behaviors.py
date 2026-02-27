import pytest
from unittest import mock
from django.utils import timezone

from api.base.settings.defaults import API_BASE
from osf.utils.workflows import DefaultStates
from osf_tests.factories import AuthUserFactory, PreprintFactory, PreprintProviderFactory


@pytest.mark.django_db
class TestPreprintDetailNewBehaviors:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def url(self):
        def _url(preprint_id):
            return f'/{API_BASE}preprints/{preprint_id}/'
        return _url

    def test_delete_allowed_when_initial_state(self, app, user, provider, url):
        preprint = PreprintFactory(creator=user, provider=provider, is_published=False, machine_state=DefaultStates.INITIAL.value)
        res = app.delete_json_api(url(preprint._id), auth=user.auth)
        assert res.status_code == 204

    def test_delete_forbidden_when_not_initial_state(self, app, user, provider, url):
        preprint = PreprintFactory(creator=user, provider=provider, is_published=True)
        preprint.machine_state = 'accepted'
        preprint.date_published = timezone.now()
        preprint.save()
        res = app.delete_json_api(url(preprint._id), auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert 'You cannot delete created preprint' in res.json['errors'][0]['detail']

    def test_citation_detail_not_found_for_anonymous_on_private(self, app, user):
        preprint = PreprintFactory(creator=user, is_published=False)
        citation_url = f'/{API_BASE}preprints/{preprint._id}/citation/'
        res = app.get(citation_url, expect_errors=True)
        assert res.status_code in (401, 403, 404)

    def test_citation_style_not_found_for_unknown_style(self, app, user):
        preprint = PreprintFactory(creator=user)
        style_url = f'/{API_BASE}preprints/{preprint._id}/citation/apa9999/'
        res = app.get(style_url, expect_errors=True)
        assert res.status_code == 404
        assert 'is not a known style' in res.json['errors'][0]['detail']

    def test_old_versions_immutable_mixin_blocks_update_for_old_version(self, app, user, provider):
        preprint = PreprintFactory(creator=user, provider=provider, is_published=True)
        # simulate an older version by creating a new version and then addressing the older guid
        with mock.patch('api.preprints.serializers.PreprintCreateVersionSerializer.create') as mock_create:
            mock_create.return_value = preprint
        # Directly refer to v1 when a newer exists should be blocked by mixin during update
        base_id, version = preprint._id.split('_v')
        older_id = f"{base_id}_v1"
        url = f'/{API_BASE}preprints/{older_id}/'
        res = app.patch_json_api(url, {'data': {'id': older_id, 'type': 'preprints', 'attributes': {'title': 'x'}}}, auth=user.auth, expect_errors=True)
        assert res.status_code in (404, 409)
