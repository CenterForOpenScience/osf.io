import pytest

from django.utils import timezone
from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf.models import PreprintLog
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
)
from rest_framework import exceptions
from tests.utils import assert_latest_log, assert_latest_log_not
from osf.utils import permissions
from osf.utils.workflows import DefaultStates
from api_tests.utils import disconnected_from_listeners
from website.project.signals import contributor_removed

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.mark.django_db
@pytest.mark.enable_implicit_clean
class TestPreprintContributorDetail:

    @pytest.fixture()
    def title(self):
        return 'Cool Preprint'

    @pytest.fixture()
    def description(self):
        return 'A Properly Cool Preprint'

    @pytest.fixture()
    def preprint_published(
            self, user, title, description):
        return PreprintFactory(
            title=title,
            description=description,
            is_published=True,
            creator=user
        )

    @pytest.fixture()
    def preprint_unpublished(
            self, user, title, description):
        return PreprintFactory(
            title=title,
            description=description,
            is_published=False,
            creator=user
        )

    @pytest.fixture()
    def url_published(self, user, preprint_published):
        return '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint_published._id, user._id)

    @pytest.fixture()
    def url_unpublished_base(self, preprint_unpublished):
        return '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint_unpublished._id, '{}')

    @pytest.fixture()
    def url_unpublished(self, user, url_unpublished_base):
        return url_unpublished_base.format(user._id)

    def test_get_contributor_detail_valid_response(
            self, app, user, preprint_published,
            preprint_unpublished, url_published, url_unpublished):

        #   test_get_public_contributor_detail
        res = app.get(url_published)
        assert res.status_code == 200
        assert res.json['data']['id'] == '{}-{}'.format(
            preprint_published._id, user._id)

    #   regression test
    #   test_get_public_contributor_detail_is_viewable_through_browsable_api
        res = app.get(url_published + '?format=api')
        assert res.status_code == 200

    #   test_get_private_node_contributor_detail_contributor_auth
        res = app.get(url_unpublished, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == '{}-{}'.format(
            preprint_unpublished._id, user._id)

    def test_get_contributor_detail_errors(
            self, app, user, url_unpublished_base, url_unpublished):
        non_contrib = AuthUserFactory()

    #   test_get_private_node_contributor_detail_non_contributor
        res = app.get(url_unpublished, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_get_private_node_contributor_detail_not_logged_in
        res = app.get(url_unpublished, expect_errors=True)
        assert res.status_code == 401

    #   test_get_private_node_non_contributor_detail_contributor_auth
        res = app.get(
            url_unpublished_base.format(
                non_contrib._id),
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

    #   test_get_private_node_invalid_user_detail_contributor_auth
        res = app.get(
            url_unpublished_base.format('invalid'),
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

    def test_unregistered_contributor_detail_show_up_as_name_associated_with_preprint(
            self,
            app,
            user,
            preprint_published):
        preprint_published.add_unregistered_contributor(
            'Rheisen Dennis',
            'reason@gmail.com',
            auth=Auth(user),
            save=True)
        unregistered_contributor = preprint_published.contributors[1]
        url = '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint_published._id, unregistered_contributor._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['embeds']['users']['data']['attributes']['full_name'] == 'Rheisen Dennis'
        assert res.json['data']['attributes'].get(
            'unregistered_contributor') == 'Rheisen Dennis'

        preprint_two = PreprintFactory(creator=user, is_public=True)
        preprint_two.add_unregistered_contributor(
            'Nesiehr Sinned', 'reason@gmail.com', auth=Auth(user), save=True)
        url = '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint_two._id, unregistered_contributor._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 200

        assert res.json['data']['embeds']['users']['data']['attributes']['full_name'] == 'Rheisen Dennis'
        assert res.json['data']['attributes'].get(
            'unregistered_contributor') == 'Nesiehr Sinned'

    def test_detail_includes_index(
            self,
            app,
            user,
            preprint_published,
            url_published):
        res = app.get(url_published)
        data = res.json['data']
        assert 'index' in data['attributes'].keys()
        assert data['attributes']['index'] == 0

        other_contributor = AuthUserFactory()
        preprint_published.add_contributor(
            other_contributor, auth=Auth(user), save=True)

        other_contributor_detail = '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint_published._id, other_contributor._id)
        res = app.get(other_contributor_detail)
        assert res.json['data']['attributes']['index'] == 1

    def test_preprint_contributor_unpublished(
            self, app, user, preprint_unpublished, url_unpublished):
        # Unauthenticated
        res = app.get(url_unpublished, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        user_two = AuthUserFactory()
        res = app.get(url_unpublished, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        preprint_unpublished.add_contributor(user_two, permissions.WRITE, save=True)
        res = app.get(url_unpublished, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Admin contrib
        res = app.get(url_unpublished, auth=user.auth)
        assert res.status_code == 200

    def test_preprint_contributor_deleted(
            self, app, user, preprint_published, url_published):
        preprint_published.deleted = timezone.now()
        preprint_published.save()

        # Unauthenticated
        res = app.get(url_published, expect_errors=True)
        assert res.status_code == 404

        # Noncontrib
        user_two = AuthUserFactory()
        res = app.get(url_published, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 404

        # Write contrib
        preprint_published.add_contributor(user_two, permissions.WRITE, save=True)
        res = app.get(url_published, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 404

        # Admin contrib
        res = app.get(url_published, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    def test_preprint_contributor_private(
            self, app, user, preprint_published, url_published):
        preprint_published.is_public = False
        preprint_published.save()

        # Unauthenticated
        res = app.get(url_published, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        user_two = AuthUserFactory()
        res = app.get(url_published, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        preprint_published.add_contributor(user_two, permissions.WRITE, save=True)
        res = app.get(url_published, auth=user_two.auth)
        assert res.status_code == 200

        # Admin contrib
        res = app.get(url_published, auth=user.auth)
        assert res.status_code == 200

    def test_preprint_contributor_abandoned(
            self, app, user, preprint_published, url_published):
        preprint_published.machine_state = DefaultStates.INITIAL.value
        preprint_published.save()

        # Unauthenticated
        res = app.get(url_published, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        user_two = AuthUserFactory()
        res = app.get(url_published, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        preprint_published.add_contributor(user_two, permissions.WRITE, save=True)
        res = app.get(url_published, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Admin contrib
        res = app.get(url_published, auth=user.auth)
        assert res.status_code == 200

    def test_preprint_contributor_orphaned(
            self, app, user, preprint_published, url_published):
        preprint_published.primary_file = None
        preprint_published.save()

        # Unauthenticated
        res = app.get(url_published, expect_errors=True)
        assert res.status_code == 401

        # Noncontrib
        user_two = AuthUserFactory()
        res = app.get(url_published, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        # Write contrib
        preprint_published.add_contributor(user_two, permissions.WRITE, save=True)
        res = app.get(url_published, auth=user_two.auth)
        assert res.status_code == 200

        # Admin contrib
        res = app.get(url_published, auth=user.auth)
        assert res.status_code == 200


@pytest.mark.django_db
class TestPreprintContributorOrdering:

    @pytest.fixture()
    def contribs(self, user):
        return [user] + [AuthUserFactory() for _ in range(9)]

    @pytest.fixture()
    def preprint(self, user, contribs):
        preprint = PreprintFactory(creator=user)
        for contrib in contribs:
            if contrib._id != user._id:
                preprint.add_contributor(
                    contrib,
                    permissions=permissions.WRITE,
                    visible=True,
                    save=True
                )
        return preprint

    @pytest.fixture()
    def url_contrib_base(self, preprint):
        return '/{}preprints/{}/contributors/'.format(API_BASE, preprint._id)

    @pytest.fixture()
    def url_creator(self, user, preprint):
        return '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint._id, user._id)

    @pytest.fixture()
    def urls_contrib(self, contribs, preprint):
        return [
            '/{}preprints/{}/contributors/{}/'.format(
                API_BASE,
                preprint._id,
                contrib._id) for contrib in contribs]

    @pytest.fixture()
    def last_position(self, contribs):
        return len(contribs) - 1

    @staticmethod
    @pytest.fixture()
    def contrib_user_id():
        def get_contrib_user_id(contributor):
            return contributor['embeds']['users']['data']['id']
        return get_contrib_user_id

    def test_initial_order(
            self, app, user, contribs, preprint, contrib_user_id):
        res = app.get('/{}preprints/{}/contributors/'.format(
            API_BASE, preprint._id), auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        found_contributors = False
        for i in range(len(contribs)):
            assert contribs[i]._id == contrib_user_id(contributor_list[i])
            assert i == contributor_list[i]['attributes']['index']
            found_contributors = True
        assert found_contributors, 'Did not compare any contributors.'

    def test_move_top_contributor_down_one_and_also_log(
            self, app, user, contribs, preprint, contrib_user_id, url_contrib_base):
        with assert_latest_log(PreprintLog.CONTRIB_REORDERED, preprint):
            contributor_to_move = contribs[0]._id
            contributor_id = '{}-{}'.format(preprint._id, contributor_to_move)
            former_second_contributor = contribs[1]
            url = '{}{}/'.format(url_contrib_base, contributor_to_move)
            data = {
                'data': {
                    'id': contributor_id,
                    'type': 'contributors',
                    'attributes': {
                        'index': 1
                    }
                }
            }
            res_patch = app.patch_json_api(url, data, auth=user.auth)
            assert res_patch.status_code == 200
            preprint.reload()
            res = app.get(
                '/{}preprints/{}/contributors/'.format(API_BASE, preprint._id), auth=user.auth)
            assert res.status_code == 200
            contributor_list = res.json['data']
            assert contrib_user_id(contributor_list[1]) == contributor_to_move
            assert contrib_user_id(
                contributor_list[0]) == former_second_contributor._id

    def test_move_second_contributor_up_one_to_top(
            self, app, user, contribs, preprint,
            contrib_user_id, url_contrib_base):
        contributor_to_move = contribs[1]._id
        contributor_id = '{}-{}'.format(preprint._id, contributor_to_move)
        former_first_contributor = contribs[0]
        url = '{}{}/'.format(url_contrib_base, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': 0
                }
            }
        }
        res_patch = app.patch_json_api(url, data, auth=user.auth)
        assert res_patch.status_code == 200
        preprint.reload()
        res = app.get('/{}preprints/{}/contributors/'.format(
            API_BASE, preprint._id), auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert contrib_user_id(contributor_list[0]) == contributor_to_move
        assert contrib_user_id(
            contributor_list[1]) == former_first_contributor._id

    def test_move_top_contributor_down_to_bottom(
            self, app, user, contribs, preprint,
            contrib_user_id, last_position,
            url_contrib_base):
        contributor_to_move = contribs[0]._id
        contributor_id = '{}-{}'.format(preprint._id, contributor_to_move)
        former_second_contributor = contribs[1]
        url = '{}{}/'.format(url_contrib_base, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': last_position
                }
            }
        }
        res_patch = app.patch_json_api(url, data, auth=user.auth)
        assert res_patch.status_code == 200
        preprint.reload()
        res = app.get('/{}preprints/{}/contributors/'.format(API_BASE,
                                                         preprint._id), auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert contrib_user_id(
            contributor_list[last_position]) == contributor_to_move
        assert contrib_user_id(
            contributor_list[0]) == former_second_contributor._id

    def test_move_bottom_contributor_up_to_top(
            self, app, user, contribs, preprint,
            contrib_user_id, last_position,
            url_contrib_base):
        contributor_to_move = contribs[last_position]._id
        contributor_id = '{}-{}'.format(preprint._id, contributor_to_move)
        former_second_to_last_contributor = contribs[last_position - 1]

        url = '{}{}/'.format(url_contrib_base, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': 0
                }
            }
        }
        res_patch = app.patch_json_api(url, data, auth=user.auth)
        assert res_patch.status_code == 200
        preprint.reload()
        res = app.get('/{}preprints/{}/contributors/'.format(API_BASE,
                                                         preprint._id), auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert contrib_user_id(contributor_list[0]) == contributor_to_move
        assert (
            contrib_user_id(contributor_list[last_position]) ==
            former_second_to_last_contributor._id)

    def test_move_second_to_last_contributor_down_past_bottom(
            self, app, user, contribs, preprint,
            contrib_user_id, last_position,
            url_contrib_base):
        contributor_to_move = contribs[last_position - 1]._id
        contributor_id = '{}-{}'.format(preprint._id, contributor_to_move)
        former_last_contributor = contribs[last_position]

        url = '{}{}/'.format(url_contrib_base, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': last_position + 10
                }
            }
        }
        res_patch = app.patch_json_api(url, data, auth=user.auth)
        assert res_patch.status_code == 200
        preprint.reload()
        res = app.get('/{}preprints/{}/contributors/'.format(API_BASE,
                                                         preprint._id), auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert contrib_user_id(
            contributor_list[last_position]) == contributor_to_move
        assert (
            contrib_user_id(contributor_list[last_position - 1]) ==
            former_last_contributor._id)

    def test_move_top_contributor_down_to_second_to_last_position_with_negative_numbers(
            self, app, user, contribs, preprint, contrib_user_id, last_position, url_contrib_base):
        contributor_to_move = contribs[0]._id
        contributor_id = '{}-{}'.format(preprint._id, contributor_to_move)
        former_second_contributor = contribs[1]
        url = '{}{}/'.format(url_contrib_base, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': -1
                }
            }
        }
        res_patch = app.patch_json_api(url, data, auth=user.auth)
        assert res_patch.status_code == 200
        preprint.reload()
        res = app.get('/{}preprints/{}/contributors/'.format(API_BASE,
                                                         preprint._id), auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert contrib_user_id(
            contributor_list[last_position - 1]) == contributor_to_move
        assert contrib_user_id(
            contributor_list[0]) == former_second_contributor._id

    def test_write_contributor_fails_to_move_top_contributor_down_one(
            self, app, user, contribs, preprint, contrib_user_id, url_contrib_base):
        contributor_to_move = contribs[0]._id
        contributor_id = '{}-{}'.format(preprint._id, contributor_to_move)
        former_second_contributor = contribs[1]
        url = '{}{}/'.format(url_contrib_base, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': 1
                }
            }
        }
        res_patch = app.patch_json_api(
            url, data,
            auth=former_second_contributor.auth,
            expect_errors=True)
        assert res_patch.status_code == 403
        preprint.reload()
        res = app.get('/{}preprints/{}/contributors/'.format(API_BASE,
                                                         preprint._id), auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert contrib_user_id(contributor_list[0]) == contributor_to_move
        assert contrib_user_id(
            contributor_list[1]) == former_second_contributor._id

    def test_non_authenticated_fails_to_move_top_contributor_down_one(
            self, app, user, contribs, preprint, contrib_user_id, url_contrib_base):
        contributor_to_move = contribs[0]._id
        contributor_id = '{}-{}'.format(preprint._id, contributor_to_move)
        former_second_contributor = contribs[1]
        url = '{}{}/'.format(url_contrib_base, contributor_to_move)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'index': 1
                }
            }
        }
        res_patch = app.patch_json_api(url, data, expect_errors=True)
        assert res_patch.status_code == 401
        preprint.reload()
        res = app.get('/{}preprints/{}/contributors/'.format(
            API_BASE, preprint._id), auth=user.auth)
        assert res.status_code == 200
        contributor_list = res.json['data']
        assert contrib_user_id(contributor_list[0]) == contributor_to_move
        assert contrib_user_id(
            contributor_list[1]) == former_second_contributor._id


@pytest.mark.django_db
class TestPreprintContributorUpdate:

    @pytest.fixture()
    def contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint(self, user, contrib):
        preprint = PreprintFactory(creator=user)
        preprint.add_contributor(
            contrib,
            permissions=permissions.WRITE,
            visible=True,
            save=True)
        return preprint

    @pytest.fixture()
    def url_creator(self, user, preprint):
        return '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint._id, user._id)

    @pytest.fixture()
    def url_contrib(self, preprint, contrib):
        return '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint._id, contrib._id)

    def test_change_contrib_errors(
            self, app, user, contrib, preprint, url_contrib):

        #   test_change_contributor_no_id
        data = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = app.put_json_api(
            url_contrib,
            data,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400

    #   test_change_contributor_incorrect_id
        data = {
            'data': {
                'id': '12345',
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = app.put_json_api(
            url_contrib,
            data,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 409

    #   test_change_contributor_no_type
        contrib_id = '{}-{}'.format(preprint._id, contrib._id)
        data = {
            'data': {
                'id': contrib_id,
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = app.put_json_api(
            url_contrib, data,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400

    #   test_change_contributor_incorrect_type
        data = {
            'data': {
                'id': contrib._id,
                'type': 'Wrong type.',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = app.put_json_api(
            url_contrib, data,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 409

    #   test_invalid_change_inputs_contributor
        contrib_id = '{}-{}'.format(preprint._id, contrib._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'permission': 'invalid',
                    'bibliographic': 'invalid'
                }
            }
        }
        res = app.put_json_api(
            url_contrib, data,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert set(preprint.get_permissions(contrib)) == set(['read_preprint', 'write_preprint'])
        assert preprint.get_visible(contrib)

    #   test_change_contributor_not_logged_in
        data = {
            'data': {
                'id': contrib._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                    'bibliographic': False
                }
            }
        }
        res = app.put_json_api(url_contrib, data, expect_errors=True)
        assert res.status_code == 401

        preprint.reload()
        assert set(preprint.get_permissions(contrib)) == set(['read_preprint', 'write_preprint'])
        assert preprint.get_visible(contrib)

    #   test_change_contributor_non_admin_auth
        data = {
            'data': {
                'id': contrib._id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                    'bibliographic': False
                }
            }
        }
        res = app.put_json_api(
            url_contrib, data,
            auth=contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

        preprint.reload()
        assert set(preprint.get_permissions(contrib)) == set(['read_preprint', 'write_preprint'])
        assert preprint.get_visible(contrib)

    def test_change_admin_self_without_other_admin(
            self, app, user, preprint, url_creator):
        contrib_id = '{}-{}'.format(preprint._id, user._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.WRITE,
                    'bibliographic': True
                }
            }
        }
        res = app.put_json_api(
            url_creator, data,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400

        preprint.reload()
        assert set(preprint.get_permissions(user)) == set(['read_preprint', 'write_preprint', 'admin_preprint'])

    def test_node_update_invalid_data(self, app, user, url_creator):
        res = app.put_json_api(
            url_creator,
            'Incorrect data',
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

        res = app.put_json_api(
            url_creator,
            ['Incorrect data'],
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    def test_change_contributor_correct_id(
            self, app, user, contrib, preprint, url_contrib):
        contrib_id = '{}-{}'.format(preprint._id, contrib._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.ADMIN,
                    'bibliographic': True
                }
            }
        }
        res = app.put_json_api(
            url_contrib, data,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 200

    def test_remove_all_bibliographic_statuses_contributors(
            self, app, user, contrib, preprint, url_creator):
        preprint.set_visible(contrib, False, save=True)
        contrib_id = '{}-{}'.format(preprint._id, user._id)
        data = {
            'data': {
                'id': contrib_id,
                'type': 'contributors',
                'attributes': {
                    'bibliographic': False
                }
            }
        }
        res = app.put_json_api(
            url_creator, data,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400

        preprint.reload()
        assert preprint.get_visible(user)

    def test_change_contributor_permissions(
            self, app, user, contrib, preprint, url_contrib):
        contrib_id = '{}-{}'.format(preprint._id, contrib._id)

        with assert_latest_log(PreprintLog.PERMISSIONS_UPDATED, preprint):
            data = {
                'data': {
                    'id': contrib_id,
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.ADMIN,
                        'bibliographic': True
                    }
                }
            }
            res = app.put_json_api(url_contrib, data, auth=user.auth)
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['permission'] == permissions.ADMIN

            preprint.reload()
            assert set(preprint.get_permissions(contrib)) == set([
                'read_preprint', 'write_preprint', 'admin_preprint'])

        with assert_latest_log(PreprintLog.PERMISSIONS_UPDATED, preprint):
            data = {
                'data': {
                    'id': contrib_id,
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.WRITE,
                        'bibliographic': True
                    }
                }
            }
            res = app.put_json_api(url_contrib, data, auth=user.auth)
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['permission'] == permissions.WRITE

            preprint.reload()
            assert set(preprint.get_permissions(contrib)) == set([
                'read_preprint', 'write_preprint'])

        with assert_latest_log(PreprintLog.PERMISSIONS_UPDATED, preprint):
            data = {
                'data': {
                    'id': contrib_id,
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.READ,
                        'bibliographic': True
                    }
                }
            }
            res = app.put_json_api(url_contrib, data, auth=user.auth)
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['permission'] == permissions.READ

            preprint.reload()
            assert set(preprint.get_permissions(contrib)) == set(['read_preprint'])

    def test_change_contributor_bibliographic(
            self, app, user, contrib, preprint, url_contrib):
        contrib_id = '{}-{}'.format(preprint._id, contrib._id)
        with assert_latest_log(PreprintLog.MADE_CONTRIBUTOR_INVISIBLE, preprint):
            data = {
                'data': {
                    'id': contrib_id,
                    'type': 'contributors',
                    'attributes': {
                        'bibliographic': False
                    }
                }
            }
            res = app.put_json_api(url_contrib, data, auth=user.auth)
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert not attributes['bibliographic']

            preprint.reload()
            assert not preprint.get_visible(contrib)

        with assert_latest_log(PreprintLog.MADE_CONTRIBUTOR_VISIBLE, preprint):
            data = {
                'data': {
                    'id': contrib_id,
                    'type': 'contributors',
                    'attributes': {
                        'bibliographic': True
                    }
                }
            }
            res = app.put_json_api(url_contrib, data, auth=user.auth)
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['bibliographic']

            preprint.reload()
            assert preprint.get_visible(contrib)

    def test_change_contributor_permission_and_bibliographic(
            self, app, user, contrib, preprint, url_contrib):
        with assert_latest_log(PreprintLog.PERMISSIONS_UPDATED, preprint, 1), assert_latest_log(PreprintLog.MADE_CONTRIBUTOR_INVISIBLE, preprint):
            contrib_id = '{}-{}'.format(preprint._id, contrib._id)
            data = {
                'data': {
                    'id': contrib_id,
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.READ,
                        'bibliographic': False
                    }
                }
            }
            res = app.put_json_api(url_contrib, data, auth=user.auth)
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['permission'] == permissions.READ
            assert not attributes['bibliographic']

            preprint.reload()
            assert set(preprint.get_permissions(contrib)) == set(['read_preprint'])
            assert not preprint.get_visible(contrib)

    # @assert_not_logs(PreprintLog.PERMISSIONS_UPDATED, 'preprint')
    def test_not_change_contributor(
            self, app, user, contrib, preprint, url_contrib):
        with assert_latest_log_not(PreprintLog.PERMISSIONS_UPDATED, preprint):
            contrib_id = '{}-{}'.format(preprint._id, contrib._id)
            data = {
                'data': {
                    'id': contrib_id,
                    'type': 'contributors',
                    'attributes': {
                        'permission': None,
                        'bibliographic': True
                    }
                }
            }
            res = app.put_json_api(url_contrib, data, auth=user.auth)
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['permission'] == permissions.WRITE
            assert attributes['bibliographic']

            preprint.reload()
            assert set(preprint.get_permissions(contrib)) == set([
                'read_preprint', 'write_preprint'])
            assert preprint.get_visible(contrib)

    def test_change_admin_self_with_other_admin(
            self, app, user, contrib, preprint, url_creator):
        with assert_latest_log(PreprintLog.PERMISSIONS_UPDATED, preprint):
            preprint.add_permission(contrib, permissions.ADMIN, save=True)
            contrib_id = '{}-{}'.format(preprint._id, user._id)
            data = {
                'data': {
                    'id': contrib_id,
                    'type': 'contributors',
                    'attributes': {
                        'permission': permissions.WRITE,
                        'bibliographic': True
                    }
                }
            }
            res = app.put_json_api(url_creator, data, auth=user.auth)
            assert res.status_code == 200
            attributes = res.json['data']['attributes']
            assert attributes['permission'] == permissions.WRITE

            preprint.reload()
            assert set(preprint.get_permissions(user)) == set([
                'read_preprint', 'write_preprint'])


@pytest.mark.django_db
class TestPreprintContributorPartialUpdate:

    @pytest.fixture()
    def contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint(self, user, contrib):
        preprint = PreprintFactory(creator=user)
        preprint.add_contributor(
            contrib,
            permissions=permissions.WRITE,
            visible=True,
            save=True)
        return preprint

    @pytest.fixture()
    def url_creator(self, user, preprint):
        return '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint._id, user._id)

    @pytest.fixture()
    def url_contrib(self, contrib, preprint):
        return '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, self.preprint._id, self.user_two._id)

    def test_patch_bibliographic_only(self, app, user, preprint, url_creator):
        creator_id = '{}-{}'.format(preprint._id, user._id)
        data = {
            'data': {
                'id': creator_id,
                'type': 'contributors',
                'attributes': {
                    'bibliographic': False,
                }
            }
        }
        res = app.patch_json_api(url_creator, data, auth=user.auth)
        assert res.status_code == 200
        preprint.reload()
        assert set(preprint.get_permissions(user)) == set([
            'read_preprint', 'write_preprint', 'admin_preprint'])
        assert not preprint.get_visible(user)

    def test_patch_permission_only(self, app, user, preprint):
        user_read_contrib = AuthUserFactory()
        preprint.add_contributor(
            user_read_contrib,
            permissions=permissions.WRITE,
            visible=False,
            save=True)
        url_read_contrib = '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint._id, user_read_contrib._id)
        contributor_id = '{}-{}'.format(preprint._id, user_read_contrib._id)
        data = {
            'data': {
                'id': contributor_id,
                'type': 'contributors',
                'attributes': {
                    'permission': permissions.READ,
                }
            }
        }
        res = app.patch_json_api(url_read_contrib, data, auth=user.auth)
        assert res.status_code == 200
        preprint.reload()
        assert set(preprint.get_permissions(user_read_contrib)) == set(['read_preprint'])
        assert not preprint.get_visible(user_read_contrib)


@pytest.mark.django_db
class TestPreprintContributorDelete:

    @pytest.fixture()
    def user_write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint(self, user, user_write_contrib):
        preprint = PreprintFactory(creator=user)
        preprint.add_contributor(
            user_write_contrib,
            permissions=permissions.WRITE,
            visible=True, save=True)
        return preprint

    @pytest.fixture()
    def url_user(self, preprint, user):
        return '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint._id, user._id)

    @pytest.fixture()
    def url_user_write_contrib(self, preprint, user_write_contrib):
        return '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint._id, user_write_contrib._id)

    @pytest.fixture()
    def url_user_non_contrib(self, preprint, user_non_contrib):
        return '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint._id, user_non_contrib._id)

    def test_remove_errors(
            self, app, user, user_write_contrib,
            user_non_contrib, preprint, url_user,
            url_user_write_contrib, url_user_non_contrib):

        #   test_remove_contributor_non_contributor
        res = app.delete(
            url_user_write_contrib,
            auth=user_non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

        preprint.reload()
        assert user_write_contrib in preprint.contributors

    #   test_remove_contributor_not_logged_in
        res = app.delete(url_user_write_contrib, expect_errors=True)
        assert res.status_code == 401

        preprint.reload()
        assert user_write_contrib in preprint.contributors

    #   test_remove_non_contributor_admin
        assert user_non_contrib not in preprint.contributors
        res = app.delete(
            url_user_non_contrib,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 404

        preprint.reload()
        assert user_non_contrib not in preprint.contributors

    #   test_remove_non_existing_user_admin
        url_user_fake = '/{}preprints/{}/contributors/{}/'.format(
            API_BASE, preprint._id, 'fake')
        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            res = app.delete(url_user_fake, auth=user.auth, expect_errors=True)
        assert res.status_code == 404

    #   test_remove_self_contributor_unique_admin
        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            res = app.delete(url_user, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        preprint.reload()
        assert user in preprint.contributors

    def test_can_not_remove_only_bibliographic_contributor(
            self, app, user, preprint, user_write_contrib, url_user):
        preprint.add_permission(
            user_write_contrib,
            permissions.ADMIN,
            save=True)
        preprint.set_visible(user_write_contrib, False, save=True)
        res = app.delete(url_user, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        preprint.reload()
        assert user in preprint.contributors

    def test_remove_contributor_non_admin_is_forbidden(
            self, app, user_write_contrib,
            user_non_contrib, preprint,
            url_user_non_contrib):
        preprint.add_contributor(
            user_non_contrib,
            permissions=permissions.WRITE,
            visible=True,
            save=True)

        res = app.delete(
            url_user_non_contrib,
            auth=user_write_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

        preprint.reload()
        assert user_non_contrib in preprint.contributors

    # @assert_logs(PreprintLog.CONTRIB_REMOVED, 'preprint')
    def test_remove_contributor_admin(
            self, app, user, user_write_contrib,
            preprint, url_user_write_contrib):
        with assert_latest_log(PreprintLog.CONTRIB_REMOVED, preprint):
            # Disconnect contributor_removed so that we don't check in files
            # We can remove this when StoredFileNode is implemented in
            # osf-models
            with disconnected_from_listeners(contributor_removed):
                res = app.delete(url_user_write_contrib, auth=user.auth)
            assert res.status_code == 204

            preprint.reload()
            assert user_write_contrib not in preprint.contributors

    # @assert_logs(PreprintLog.CONTRIB_REMOVED, 'preprint')
    def test_remove_self_non_admin(
            self, app, user_non_contrib,
            preprint, url_user_non_contrib):
        preprint.add_contributor(
            user_non_contrib,
            permissions=permissions.WRITE,
            visible=True,
            save=True)

        res = app.delete(
            url_user_non_contrib,
            auth=user_non_contrib.auth)
        assert res.status_code == 204

        preprint.reload()
        assert user_non_contrib not in preprint.contributors

    # @assert_logs(PreprintLog.CONTRIB_REMOVED, 'preprint')
    def test_remove_self_contributor_not_unique_admin(
            self, app, user, user_write_contrib, preprint, url_user):
        with assert_latest_log(PreprintLog.CONTRIB_REMOVED, preprint):
            preprint.add_permission(
                user_write_contrib,
                permissions.ADMIN,
                save=True)

            res = app.delete(url_user, auth=user.auth)
            assert res.status_code == 204

            preprint.reload()
            assert user not in preprint.contributors

    # @assert_logs(PreprintLog.CONTRIB_REMOVED, 'preprint')
    def test_can_remove_self_as_contributor_not_unique_admin(
            self, app, user_write_contrib, preprint, url_user_write_contrib):
        with assert_latest_log(PreprintLog.CONTRIB_REMOVED, preprint):
            preprint.add_permission(
                user_write_contrib,
                permissions.ADMIN,
                save=True)

            res = app.delete(
                url_user_write_contrib,
                auth=user_write_contrib.auth)
            assert res.status_code == 204

            preprint.reload()
            assert user_write_contrib not in preprint.contributors
