import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    OSFGroupFactory,
)

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def manager():
    return AuthUserFactory()

@pytest.fixture()
def member():
    return AuthUserFactory()

@pytest.fixture()
def old_name():
    return 'Platform Team'

@pytest.fixture()
def osf_group(manager, member, old_name):
    group = OSFGroupFactory(name=old_name, creator=manager)
    group.make_member(member)
    return group

@pytest.fixture()
def url(osf_group):
    return '/{}osf_groups/{}/managers/'.format(API_BASE, osf_group._id)


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOSFGroupManagersList:
    def test_return_perms(self, app, member, manager, user, osf_group, url):
        # test unauthenticated
        res = app.get(url)
        assert res.status_code == 200

        # test user
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        # test member
        res = app.get(url, auth=member.auth)
        assert res.status_code == 200

        # test manager
        res = app.get(url, auth=manager.auth)
        assert res.status_code == 200

        # test invalid group
        url = '/{}osf_groups/{}/managers/'.format(API_BASE, '12345_bad_id')
        res = app.get(url, auth=manager.auth, expect_errors=True)
        assert res.status_code == 404

    def test_allowed_methods(self, app, manager, url):
        res = app.post_json_api(url, {}, auth=manager.auth, expect_errors=True)
        assert res.status_code == 405

        res = app.patch_json_api(url, {}, auth=manager.auth, expect_errors=True)
        assert res.status_code == 405

        res = app.put_json_api(url, {}, auth=manager.auth, expect_errors=True)
        assert res.status_code == 405

        res = app.delete_json_api(url, auth=manager.auth, expect_errors=True)
        assert res.status_code == 405

    def test_return_managers(self, app, member, manager, user, osf_group, url):
        res = app.get(url)
        data = res.json['data']
        assert len(data) == 1
        assert data[0]['id'] == manager._id

        osf_group.make_manager(member)
        res = app.get(url)
        data = res.json['data']
        assert len(data) == 2
        manager_ids = [man['id'] for man in data]
        assert manager._id in manager_ids
        assert member._id in manager_ids
