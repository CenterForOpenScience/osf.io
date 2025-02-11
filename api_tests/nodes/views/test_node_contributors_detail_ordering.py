import pytest

from api.base.settings.defaults import API_BASE
from osf.models import NodeLog
from osf_tests.factories import ProjectFactory, AuthUserFactory
from tests.utils import assert_latest_log
from osf.utils import permissions


@pytest.mark.django_db
class TestNodeContributorOrdering:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def contribs(self, user):
        return [user] + [AuthUserFactory() for _ in range(9)]

    @pytest.fixture()
    def project(self, user, contribs):
        project = ProjectFactory(creator=user)
        for contrib in contribs:
            if contrib._id != user._id:
                project.add_contributor(
                    contrib,
                    permissions=permissions.WRITE,
                    visible=True,
                    save=True
                )
        return project

    @pytest.fixture()
    def url_contrib_base(self, project):
        return f'/{API_BASE}nodes/{project._id}/contributors/'

    @pytest.fixture()
    def url_creator(self, user, project):
        return f'/{API_BASE}nodes/{project._id}/contributors/{user._id}/'

    @pytest.fixture()
    def urls_contrib(self, contribs, project):
        return [f'/{API_BASE}nodes/{project._id}/contributors/{contrib._id}/' for contrib in contribs]

    @pytest.fixture()
    def last_position(self, contribs):
        return len(contribs) - 1

    def get_contrib_user_id(self, data):
        return data['embeds']['users']['data']['id']

    def test_initial_order(self, app, user, contribs, project, url_contrib_base):
        res = app.get(url_contrib_base, auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        found_contributors = False
        for i in range(len(contribs)):
            assert contribs[i]._id == self.get_contrib_user_id(contributor_list[i])
            assert i == contributor_list[i]['attributes']['index']
            found_contributors = True
        assert found_contributors, 'Did not compare any contributors.'

    def test_move_top_contributor_down_one_and_also_log(self, app, user, contribs, project, url_contrib_base):
        with assert_latest_log(NodeLog.CONTRIB_REORDERED, project):
            contributor_to_move = contribs[0]._id
            former_second_contributor = contribs[1]
            res_patch = app.patch_json_api(
                f'{url_contrib_base}{contributor_to_move}/',
                {
                    'data': {
                        'id': f'{project._id}-{contributor_to_move}',
                        'type': 'contributors',
                        'attributes': {
                            'index': 1
                        }
                    }
                },
                auth=user.auth
            )
            assert res_patch.status_code == 200

            res = app.get(url_contrib_base, auth=user.auth)
            assert res.status_code == 200
            contributor_list = res.json['data']

            assert self.get_contrib_user_id(contributor_list[1]) == contributor_to_move
            assert self.get_contrib_user_id(contributor_list[0]) == former_second_contributor._id

    def test_move_second_contributor_up_one_to_top(self, app, user, contribs, project, url_contrib_base):
        contributor_to_move = contribs[1]._id
        former_first_contributor = contribs[0]
        res_patch = app.patch_json_api(
            f'{url_contrib_base}{contributor_to_move}/',
            {
                'data': {
                    'id': f'{project._id}-{contributor_to_move}',
                    'type': 'contributors',
                    'attributes': {
                        'index': 0
                    }
                }
            },
            auth=user.auth
        )
        assert res_patch.status_code == 200
        res = app.get(url_contrib_base, auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert self.get_contrib_user_id(contributor_list[0]) == contributor_to_move
        assert self.get_contrib_user_id(contributor_list[1]) == former_first_contributor._id

    def test_move_top_contributor_down_to_bottom(self, app, user, contribs, project, last_position, url_contrib_base):
        contributor_to_move = contribs[0]._id
        former_second_contributor = contribs[1]
        res_patch = app.patch_json_api(
            f'{url_contrib_base}{contributor_to_move}/',
            {
                'data': {
                    'id': f'{project._id}-{contributor_to_move}',
                    'type': 'contributors',
                    'attributes': {
                        'index': last_position
                    }
                }
            },
            auth=user.auth
        )
        assert res_patch.status_code == 200
        res = app.get(url_contrib_base, auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert self.get_contrib_user_id(contributor_list[last_position]) == contributor_to_move
        assert self.get_contrib_user_id(contributor_list[0]) == former_second_contributor._id

    def test_move_bottom_contributor_up_to_top(self, app, user, contribs, project, last_position, url_contrib_base):
        contributor_to_move = contribs[last_position]._id
        former_second_to_last_contributor = contribs[last_position - 1]
        res_patch = app.patch_json_api(
            f'{url_contrib_base}{contributor_to_move}/',
            {
                'data': {
                    'id': f'{project._id}-{contributor_to_move}',
                    'type': 'contributors',
                    'attributes': {
                        'index': 0
                    }
                }
            },
            auth=user.auth
        )
        assert res_patch.status_code == 200
        res = app.get(url_contrib_base, auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert self.get_contrib_user_id(contributor_list[0]) == contributor_to_move
        assert self.get_contrib_user_id(contributor_list[last_position]) == former_second_to_last_contributor._id

    def test_move_second_to_last_contributor_down_past_bottom(
            self, app, user, contribs, project, last_position, url_contrib_base):
        contributor_to_move = contribs[last_position - 1]._id
        former_last_contributor = contribs[last_position]
        res_patch = app.patch_json_api(
            f'{url_contrib_base}{contributor_to_move}/',
            {
                'data': {
                    'id': f'{project._id}-{contributor_to_move}',
                    'type': 'contributors',
                    'attributes': {
                        'index': last_position + 10
                    }
                }
            },
            auth=user.auth
        )
        assert res_patch.status_code == 200
        res = app.get(url_contrib_base, auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert self.get_contrib_user_id(contributor_list[last_position]) == contributor_to_move
        assert self.get_contrib_user_id(contributor_list[last_position - 1]) == former_last_contributor._id

    def test_move_top_contributor_down_to_second_to_last_position_with_negative_numbers(
            self, app, user, contribs, project, last_position, url_contrib_base):
        contributor_to_move = contribs[0]._id
        former_second_contributor = contribs[1]
        res_patch = app.patch_json_api(
            f'{url_contrib_base}{contributor_to_move}/',
            {
                'data': {
                    'id': f'{project._id}-{contributor_to_move}',
                    'type': 'contributors',
                    'attributes': {
                        'index': -1
                    }
                }
            },
            auth=user.auth
        )
        assert res_patch.status_code == 200
        res = app.get(url_contrib_base, auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert self.get_contrib_user_id(contributor_list[last_position - 1]) == contributor_to_move
        assert self.get_contrib_user_id(contributor_list[0]) == former_second_contributor._id

    def test_write_contributor_fails_to_move_top_contributor_down_one(self, app, user, contribs, project,
                                                                      url_contrib_base):
        contributor_to_move = contribs[0]._id
        former_second_contributor = contribs[1]

        res_patch = app.patch_json_api(
            f'{url_contrib_base}{contributor_to_move}/',
            {
                'data': {
                    'id': f'{project._id}-{contributor_to_move}',
                    'type': 'contributors',
                    'attributes': {
                        'index': 1
                    }
                }
            },
            auth=former_second_contributor.auth,
            expect_errors=True
        )
        assert res_patch.status_code == 403
        res = app.get(url_contrib_base, auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert self.get_contrib_user_id(contributor_list[0]) == contributor_to_move
        assert self.get_contrib_user_id(contributor_list[1]) == former_second_contributor._id

    def test_non_authenticated_fails_to_move_top_contributor_down_one(
            self, app, user, contribs, project, url_contrib_base):
        contributor_to_move = contribs[0]._id
        former_second_contributor = contribs[1]
        res_patch = app.patch_json_api(
            f'{url_contrib_base}{contributor_to_move}/',
            {
                'data': {
                    'id': f'{project._id}-{contributor_to_move}',
                    'type': 'contributors',
                    'attributes': {
                        'index': 1
                    }
                }
            },
            expect_errors=True
        )
        assert res_patch.status_code == 401
        project.reload()
        res = app.get(url_contrib_base, auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert self.get_contrib_user_id(contributor_list[0]) == contributor_to_move
        assert self.get_contrib_user_id(contributor_list[1]) == former_second_contributor._id
