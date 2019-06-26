import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    ProjectFactory,
    OSFGroupFactory,
    AuthUserFactory,
)
from osf.utils.permissions import READ, WRITE

@pytest.fixture()
def non_contributor():
    return AuthUserFactory()

@pytest.fixture()
def admin_contributor():
    return AuthUserFactory()

@pytest.fixture()
def write_contributor():
    return AuthUserFactory()

@pytest.fixture()
def group_manager():
    user = AuthUserFactory()
    user.given_name = 'Dawn'
    user.save()
    return user

@pytest.fixture()
def group_member():
    return AuthUserFactory()

@pytest.fixture()
def group_member_and_contributor():
    return AuthUserFactory()

@pytest.fixture()
def group(group_manager, group_member, group_member_and_contributor):
    group = OSFGroupFactory(creator=group_manager)
    group.make_member(group_member)
    group.make_member(group_member_and_contributor)
    return group

@pytest.fixture()
def project(group, admin_contributor, write_contributor, group_member_and_contributor):
    project = ProjectFactory(
        creator=admin_contributor
    )
    project.add_contributor(write_contributor, WRITE)
    project.add_contributor(group_member_and_contributor, READ)
    project.add_osf_group(group)
    return project


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestNodeContributorsAndGroupMembers:
    def test_list_and_filter_contributors_and_group_members(
            self, app, project, admin_contributor, write_contributor, group_manager,
            group_member, group_member_and_contributor, non_contributor):
        url = '/{}nodes/{}/contributors_and_group_members/'.format(API_BASE, project._id)

        # unauthenticated
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # noncontributor
        res = app.get(url, auth=non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # write_contributor
        res = app.get(url, auth=write_contributor.auth, expect_errors=True)
        assert res.status_code == 200

        # group_member
        res = app.get(url, auth=group_member.auth, expect_errors=True)
        assert res.status_code == 200

        # assert all contributors and group members appear, no duplicates
        res = app.get(url, auth=admin_contributor.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 5
        expected = set([
            admin_contributor._id,
            write_contributor._id,
            group_manager._id,
            group_member._id,
            group_member_and_contributor._id
        ])
        actual = set([node['id'] for node in res.json['data']])

        assert actual == expected

        url = '/{}nodes/{}/contributors_and_group_members/?filter[given_name]={}'.format(API_BASE, project._id, group_manager.given_name)
        res = app.get(url, auth=admin_contributor.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == group_manager._id

        url = '/{}nodes/{}/contributors_and_group_members/?filter[given_name]=NOT_EVEN_A_NAME'.format(API_BASE, project._id)
        res = app.get(url, auth=admin_contributor.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 0
