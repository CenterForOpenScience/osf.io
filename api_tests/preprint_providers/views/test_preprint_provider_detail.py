import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    PreprintProviderFactory,
    AuthUserFactory,
)
from reviews.permissions import GroupHelper

@pytest.mark.django_db
class TestPreprintProviderExists:

    # Regression for https://openscience.atlassian.net/browse/OSF-7621

    @pytest.fixture()
    def preprint_provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def fake_url(self):
        return '/{}preprint_providers/fake/'.format(API_BASE)

    @pytest.fixture()
    def provider_url(self, preprint_provider):
        return '/{}preprint_providers/{}/'.format(API_BASE, preprint_provider._id)

    def test_preprint_provider_exists(self, app, provider_url, fake_url):
        detail_res = app.get(provider_url)
        assert detail_res.status_code == 200

        licenses_res = app.get('{}licenses/'.format(provider_url))
        assert licenses_res.status_code == 200

        preprints_res = app.get('{}preprints/'.format(provider_url))
        assert preprints_res.status_code == 200

        taxonomies_res = app.get('{}taxonomies/'.format(provider_url))
        assert taxonomies_res.status_code == 200

    #   test_preprint_provider_does_not_exist_returns_404
        detail_res = app.get(fake_url, expect_errors=True)
        assert detail_res.status_code == 404

        licenses_res = app.get('{}licenses/'.format(fake_url), expect_errors=True)
        assert licenses_res.status_code == 404

        preprints_res = app.get('{}preprints/'.format(fake_url), expect_errors=True)
        assert preprints_res.status_code == 404

        taxonomies_res = app.get('{}taxonomies/'.format(fake_url), expect_errors=True)
        assert taxonomies_res.status_code == 404


@pytest.mark.django_db
class TestPreprintProviderUpdate:

    def settings_payload(self, provider_id, workflow, comments_private, comments_anonymous):
        payload = {
            'data': {
                'id': provider_id,
                'attributes': {
                    'reviews_workflow': workflow,
                    'reviews_comments_private': comments_private,
                    'reviews_comments_anonymous': comments_anonymous,
                }
            }
        }
        return payload

    @pytest.fixture()
    def preprint_provider(self):
        return PreprintProviderFactory()

    @pytest.fixture()
    def admin(self, preprint_provider):
        user = AuthUserFactory()
        user.groups.add(GroupHelper(preprint_provider).get_group('admin'))
        return user

    @pytest.fixture()
    def moderator(self, preprint_provider):
        user = AuthUserFactory()
        user.groups.add(GroupHelper(preprint_provider).get_group('moderator'))
        return user

    @pytest.fixture()
    def url(self, preprint_provider):
        return '/{}preprint_providers/{}/'.format(API_BASE, preprint_provider._id)

    def test_update_reviews_settings(self, app, preprint_provider, url, admin, moderator):
        payload = self.settings_payload(preprint_provider.id, 'pre-moderation', False, False)

        # Only admin can set up moderation
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

        some_rando = AuthUserFactory()
        res = app.patch_json_api(url, payload, auth=some_rando.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.patch_json_api(url, payload, auth=moderator.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.patch_json_api(url, payload, auth=admin.auth)
        assert res.status_code == 200

        # ...but only once
        payload = self.settings_payload(preprint_provider.id, 'pre-moderation', True, True)
        res = app.patch_json_api(url, payload, auth=admin.auth, expect_errors=True)
        assert res.status_code == 409
