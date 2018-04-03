import pytest

from api.base.settings.defaults import API_BASE
from api.preprint_providers.permissions import GroupHelper
from osf_tests.factories import (
    AuthUserFactory,
    PreprintProviderFactory,
)


@pytest.mark.django_db
class TestPreprintProviderModeratorDetail:

    @pytest.fixture()
    def provider(self):
        pp = PreprintProviderFactory(name='ModArxiv')
        GroupHelper(pp).update_provider_auth_groups()
        return pp

    @pytest.fixture()
    def url(self, provider):
        return '/{}preprint_providers/{}/moderators/{{}}/'.format(API_BASE, provider._id)

    @pytest.fixture()
    def admin(self, provider):
        user = AuthUserFactory()
        GroupHelper(provider).get_group('admin').user_set.add(user)
        return user

    @pytest.fixture()
    def moderator(self, provider):
        user = AuthUserFactory()
        GroupHelper(provider).get_group('moderator').user_set.add(user)
        return user

    @pytest.fixture()
    def nonmoderator(self):
        return AuthUserFactory()

    def update_payload(self, user_id, permission_group, full_name=None):
        data = {
            'data': {
                'attributes': {
                    'permission_group': permission_group,
                },
                'type': 'moderators',
                'id': user_id
            }
        }
        if full_name:
            data['data']['attributes']['full_name'] = full_name
        return data

    def test_detail_not_authorized(self, app, url, nonmoderator, moderator, admin, provider):
        # Must be logged in
        res = app.get(url.format(admin._id), expect_errors=True)
        assert res.status_code == 401

        # Must be mod to get
        res = app.get(url.format(admin._id), auth=nonmoderator.auth, expect_errors=True)
        assert res.status_code == 403

        # Must be admin to edit
        res = app.patch_json_api(url.format(moderator._id),
                                 self.update_payload(user_id=moderator._id, permission_group='admin'),
                                 auth=nonmoderator.auth,
                                 expect_errors=True)
        assert res.status_code == 403

        # Must be logged in
        res = app.patch_json_api(url.format(moderator._id),
                                 self.update_payload(user_id=moderator._id, permission_group='admin'),
                                 expect_errors=True)
        assert res.status_code == 401

        # Must be admin to edit
        res = app.patch_json_api(url.format(moderator._id),
                                 self.update_payload(user_id=moderator._id, permission_group='admin'),
                                 auth=moderator.auth,
                                 expect_errors=True)
        assert res.status_code == 403

    def test_detail_successful_gets(self, app, url, moderator, admin, provider):
        res = app.get(url.format(moderator._id), auth=moderator.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == moderator._id
        assert res.json['data']['attributes']['permission_group'] == 'moderator'

        res = app.get(url.format(admin._id), auth=moderator.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == admin._id
        assert res.json['data']['attributes']['permission_group'] == 'admin'

        res = app.get(url.format(moderator._id), auth=admin.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == moderator._id
        assert res.json['data']['attributes']['permission_group'] == 'moderator'

        res = app.get(url.format(admin._id), auth=admin.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == admin._id
        assert res.json['data']['attributes']['permission_group'] == 'admin'

    def test_detail_updates(self, app, url, nonmoderator, moderator, admin, provider):
        # Admin makes moderator a new admin
        res = app.patch_json_api(url.format(moderator._id),
                                 self.update_payload(user_id=moderator._id, permission_group='admin'),
                                 auth=admin.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['permission_group'] == 'admin'

        # Admin makes new admin a moderator again
        res = app.patch_json_api(url.format(moderator._id),
                                 self.update_payload(user_id=moderator._id, permission_group='moderator'),
                                 auth=admin.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['permission_group'] == 'moderator'

        # Admin makes mod a mod -- No changes
        res = app.patch_json_api(url.format(moderator._id),
                                 self.update_payload(user_id=moderator._id, permission_group='moderator'),
                                 auth=admin.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['permission_group'] == 'moderator'

        # Mod has no perm, even though request would make no changes
        res = app.patch_json_api(url.format(moderator._id),
                                 self.update_payload(user_id=moderator._id, permission_group='moderator'),
                                 auth=moderator.auth,
                                 expect_errors=True)
        assert res.status_code == 403

        # Admin can't patch non-mod
        res = app.patch_json_api(url.format(nonmoderator._id),
                                 self.update_payload(user_id=nonmoderator._id, permission_group='moderator'),
                                 auth=admin.auth,
                                 expect_errors=True)
        assert res.status_code == 404

    def test_detail_cannot_remove_last_admin(self, app, url, admin, provider):
        res = app.patch_json_api(url.format(admin._id),
                                 self.update_payload(user_id=admin._id, permission_group='moderator'),
                                 auth=admin.auth,
                                 expect_errors=True)
        assert res.status_code == 400
        assert 'last admin' in res.json['errors'][0]['detail']

        res = app.delete_json_api(url.format(admin._id), auth=admin.auth, expect_errors=True)
        assert res.status_code == 400
        assert 'last admin' in res.json['errors'][0]['detail']

    def test_moderator_deletes(self, app, url, moderator, admin, provider):
        res = app.delete_json_api(url.format(admin._id), auth=moderator.auth, expect_errors=True)
        assert res.status_code == 403

        res = app.delete_json_api(url.format(moderator._id), auth=moderator.auth)
        assert res.status_code == 204

    def test_admin_delete_moderator(self, app, url, moderator, admin, provider):
        res = app.delete_json_api(url.format(moderator._id), auth=admin.auth)
        assert res.status_code == 204

    def test_admin_delete_admin(self, app, url, moderator, admin, provider):
        # Make mod an admin
        res = app.patch_json_api(url.format(moderator._id),
                                 self.update_payload(user_id=moderator._id, permission_group='admin'),
                                 auth=admin.auth)
        assert res.json['data']['attributes']['permission_group'] == 'admin'  # Sanity check

        # Admin delete admin
        res = app.delete_json_api(url.format(moderator._id), auth=admin.auth)
        assert res.status_code == 204
