# -*- coding: utf-8 -*-
import mock
import pytest
from future.moves.urllib.parse import urlparse, parse_qs
import datetime as dt

from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils.timezone import now

from api.base.settings.defaults import API_BASE
from osf.utils.sanitize import strip_html
from osf_tests.factories import (
    AuthUserFactory,
    CollectionFactory,
    ProjectFactory,
    RegionFactory,
    PrivateLinkFactory,
)
from website.views import find_bookmark_collection


@pytest.mark.django_db
class TestUserDetail:

    @pytest.fixture()
    def user_one(self):
        user_one = AuthUserFactory()
        user_one.social['twitter'] = ['rheisendennis']
        user_one.save()
        return user_one

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user_one):
        project = ProjectFactory(creator=user_one)
        return project

    @pytest.fixture()
    def view_only_link(self, project):
        view_only_link = PrivateLinkFactory(name='test user', anonymous=True)
        view_only_link.nodes.add(project)
        view_only_link.save()
        return view_only_link

    def test_get(self, app, user_one, user_two, project, view_only_link):

        #   test_gets_200
        url = '/{}users/{}/'.format(API_BASE, user_one._id)
        res = app.get(url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    #   test_get_correct_pk_user
        url = '/{}users/{}/?version=latest'.format(API_BASE, user_one._id)
        res = app.get(url)
        user_json = res.json['data']
        assert user_json['attributes']['full_name'] == user_one.fullname
        assert user_one.social['twitter'] == user_json['attributes']['social']['twitter']

    #   test_get_incorrect_pk_user_logged_in
        url = '/{}users/{}/'.format(API_BASE, user_two._id)
        res = app.get(url)
        user_json = res.json['data']
        assert user_json['attributes']['full_name'] != user_one.fullname

    #   test_returns_timezone_and_locale
        url = '/{}users/{}/'.format(API_BASE, user_one._id)
        res = app.get(url)
        attributes = res.json['data']['attributes']
        assert attributes['timezone'] == user_one.timezone
        assert attributes['locale'] == user_one.locale

    #   test_get_new_users
        url = '/{}users/{}/'.format(API_BASE, user_two._id)
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['data']['attributes']['full_name'] == user_two.fullname
        assert res.json['data']['attributes']['social'] == {}

    #   test_get_incorrect_pk_user_not_logged_in
        url = '/{}users/{}/'.format(API_BASE, user_two._id)
        res = app.get(url, auth=user_one.auth)
        user_json = res.json['data']
        assert user_json['attributes']['full_name'] != user_one.fullname
        assert user_json['attributes']['full_name'] == user_two.fullname

    #   test_user_detail_takes_profile_image_size_param
        size = 42
        url = '/{}users/{}/?profile_image_size={}'.format(
            API_BASE, user_one._id, size)
        res = app.get(url)
        user_json = res.json['data']
        profile_image_url = user_json['links']['profile_image']
        query_dict = parse_qs(
            urlparse(profile_image_url).query)
        assert int(query_dict.get('s')[0]) == size

    #   test_profile_image_in_links
        url = '/{}users/{}/'.format(API_BASE, user_one._id)
        res = app.get(url)
        user_json = res.json['data']
        assert 'profile_image' in user_json['links']

    #   user_viewed_through_anonymous_link
        url = '/{}users/{}/?view_only={}'.format(API_BASE, user_one._id, view_only_link.key)
        res = app.get(url)
        user_json = res.json['data']
        assert user_json['id'] == ''
        assert user_json['type'] == 'users'
        assert user_json['attributes'] == {}
        assert 'relationships' not in user_json
        assert user_json['links'] == {}

    def test_preprint_relationship(self, app, user_one):
        url = '/{}users/{}/'.format(API_BASE, user_one._id)
        preprint_url = '/{}users/{}/preprints/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one)
        user_json = res.json['data']
        href_url = user_json['relationships']['preprints']['links']['related']['href']
        assert preprint_url in href_url

    def test_registrations_relationship(self, app, user_one):
        url = '/{}users/{}/'.format(API_BASE, user_one._id)
        registration_url = '/{}users/{}/registrations/'.format(
            API_BASE, user_one._id)
        res = app.get(url, auth=user_one)
        user_json = res.json['data']
        href_url = user_json['relationships']['registrations']['links']['related']['href']
        assert registration_url in href_url

    def test_nodes_relationship_is_absent(self, app, user_one):
        url = '/{}users/{}/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one)
        assert 'node' not in res.json['data']['relationships'].keys()

    def test_emails_relationship(self, app, user_one):
        # test relationship does not show for anonymous request
        url = '/{}users/{}/'.format(API_BASE, user_one._id)
        res = app.get(url)
        assert 'emails' not in res.json['data']['relationships'].keys()

    def test_user_settings_relationship(self, app, user_one, user_two):
        # settings relationship does not show for anonymous request
        url = '/{}users/{}/'.format(API_BASE, user_one._id)
        res = app.get(url)
        assert 'settings' not in res.json['data']['relationships'].keys()

        # settings does not appear for a different user
        res = app.get(url, auth=user_two.auth)
        assert 'settings' not in res.json['data']['relationships'].keys()

        # settings is present for the current user
        res = app.get(url, auth=user_one.auth)
        assert 'settings' in res.json['data']['relationships'].keys()

    # Regression test for https://openscience.atlassian.net/browse/OSF-8966
    def test_browsable_api_for_user_detail(self, app, user_one):
        url = '/{}users/{}/?format=api'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200

    def test_social_values_old_version(self, app, user_one):
        socialname = 'ohhey'
        user_one.social = {'twitter': [socialname], 'github': []}
        user_one.save()
        url = '/{}users/{}/?version=2.9'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one)
        user_social_json = res.json['data']['attributes']['social']

        assert user_social_json['twitter'] == socialname
        assert user_social_json['github'] == ''
        assert 'linkedIn' not in user_social_json.keys()

        url = '/{}users/{}/?version=2.10'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one)
        user_social_json = res.json['data']['attributes']['social']

        assert user_social_json['twitter'] == [socialname]
        assert user_social_json['github'] == []
        assert 'linkedIn' not in user_social_json.keys()

@pytest.mark.django_db
@pytest.mark.enable_bookmark_creation
class TestUserRoutesNodeRoutes:

    @pytest.fixture()
    def user_one(self):
        user_one = AuthUserFactory()
        user_one.social['twitter'] = 'rheisendennis'
        user_one.save()
        return user_one

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public_user_one(self, user_one):
        return ProjectFactory(
            title='Public Project User One',
            is_public=True,
            creator=user_one)

    @pytest.fixture()
    def project_private_user_one(self, user_one):
        return ProjectFactory(
            title='Private Project User One',
            is_public=False,
            creator=user_one)

    @pytest.fixture()
    def project_deleted_user_one(self, user_one):
        return CollectionFactory(
            title='Deleted Project User One',
            is_public=False,
            creator=user_one,
            deleted=now())

    @pytest.fixture()
    def project_public_user_two(self, user_two):
        return ProjectFactory(
            title='Public Project User Two',
            is_public=True,
            creator=user_two)

    @pytest.fixture()
    def project_private_user_two(self, user_two):
        return ProjectFactory(
            title='Private Project User Two',
            is_public=False,
            creator=user_two)

    @pytest.fixture()
    def folder(self):
        return CollectionFactory()

    @pytest.fixture()
    def folder_deleted(self, user_one):
        return CollectionFactory(
            title='Deleted Folder User One',
            is_public=False,
            creator=user_one,
            deleted=now())

    @pytest.fixture()
    def bookmark_collection(self, user_one):
        return find_bookmark_collection(user_one)

    def test_get_200_responses(
            self, app, user_one, user_two,
            project_public_user_one,
            project_public_user_two,
            project_private_user_one,
            project_private_user_two,
            project_deleted_user_one,
            folder, folder_deleted,
            bookmark_collection):

        #   test_get_200_path_users_me_userone_logged_in
        url = '/{}users/me/'.format(API_BASE)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200

    #   test_get_200_path_users_me_usertwo_logged_in
        url = '/{}users/me/'.format(API_BASE)
        res = app.get(url, auth=user_two.auth)
        assert res.status_code == 200

    #   test_get_200_path_users_user_id_user_logged_in
        url = '/{}users/{}/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200

    #   test_get_200_path_users_user_id_no_user
        url = '/{}users/{}/'.format(API_BASE, user_two._id)
        res = app.get(url)
        assert res.status_code == 200

    #   test_get_200_path_users_user_id_unauthorized_user
        url = '/{}users/{}/'.format(API_BASE, user_two._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == user_two._id

    #   test_get_200_path_users_me_nodes_user_logged_in
        url = '/{}users/me/nodes/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200

        ids = {each['id'] for each in res.json['data']}
        assert project_public_user_one._id in ids
        assert project_private_user_one._id in ids
        assert project_public_user_two._id not in ids
        assert project_private_user_two._id not in ids
        assert folder._id not in ids
        assert folder_deleted._id not in ids
        assert project_deleted_user_one._id not in ids

    #   test_get_200_path_users_user_id_nodes_user_logged_in
        url = '/{}users/{}/nodes/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200

        ids = {each['id'] for each in res.json['data']}
        assert project_public_user_one._id in ids
        assert project_private_user_one._id in ids
        assert project_public_user_two._id not in ids
        assert project_private_user_two._id not in ids
        assert folder._id not in ids
        assert folder_deleted._id not in ids
        assert project_deleted_user_one._id not in ids

    #   test_get_200_path_users_user_id_nodes_no_user
        url = '/{}users/{}/nodes/'.format(API_BASE, user_one._id)
        res = app.get(url)
        assert res.status_code == 200

        # an anonymous/unauthorized user can only see the public projects
        # user_one contributes to.
        ids = {each['id'] for each in res.json['data']}
        assert project_public_user_one._id in ids
        assert project_private_user_one._id not in ids
        assert project_public_user_two._id not in ids
        assert project_private_user_two._id not in ids
        assert folder._id not in ids
        assert folder_deleted._id not in ids
        assert project_deleted_user_one._id not in ids

    #   test_get_200_path_users_user_id_nodes_unauthorized_user
        url = '/{}users/{}/nodes/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_two.auth)
        assert res.status_code == 200

        # an anonymous/unauthorized user can only see the public projects
        # user_one contributes to.
        ids = {each['id'] for each in res.json['data']}
        assert project_public_user_one._id in ids
        assert project_private_user_one._id not in ids
        assert project_public_user_two._id not in ids
        assert project_private_user_two._id not in ids
        assert folder._id not in ids
        assert folder_deleted._id not in ids
        assert project_deleted_user_one._id not in ids

    def test_embed_nodes(self, app, user_one, project_public_user_one):

        url = '/{}users/{}/?embed=nodes'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        embedded_data = res.json['data']['embeds']['nodes']['data'][0]['attributes']
        assert embedded_data['title'] == project_public_user_one.title

    def test_get_400_responses(self, app, user_one, user_two):

        #   test_get_403_path_users_me_nodes_no_user
        # TODO: change expected exception from 403 to 401 for unauthorized
        # users

        url = '/{}users/me/nodes/'.format(API_BASE)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

    #   test_get_403_path_users_me_no_user
        # TODO: change expected exception from 403 to 401 for unauthorized
        # users
        url = '/{}users/me/'.format(API_BASE)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

    #   test_get_404_path_users_user_id_me_user_logged_in
        url = '/{}users/{}/me/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 404

    #   test_get_404_path_users_user_id_me_no_user
        url = '/{}users/{}/me/'.format(API_BASE, user_one._id)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404

    #   test_get_404_path_users_user_id_me_unauthorized_user
        url = '/{}users/{}/me/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 404

    #   test_get_404_path_users_user_id_nodes_me_user_logged_in
        url = '/{}users/{}/nodes/me/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 404

    #   test_get_404_path_users_user_id_nodes_me_unauthorized_user
        url = '/{}users/{}/nodes/me/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 404

    #   test_get_404_path_users_user_id_nodes_me_no_user
        url = '/{}users/{}/nodes/me/'.format(API_BASE, user_one._id)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404

    #   test_get_404_path_nodes_me_user_logged_in
        url = '/{}nodes/me/'.format(API_BASE)
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 404

    #   test_get_404_path_nodes_me_no_user
        url = '/{}nodes/me/'.format(API_BASE)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404

    #   test_get_404_path_nodes_user_id_user_logged_in
        url = '/{}nodes/{}/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 404

    #   test_get_404_path_nodes_user_id_unauthorized_user
        url = '/{}nodes/{}/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 404

    #   test_get_404_path_nodes_user_id_no_user
        url = '/{}nodes/{}/'.format(API_BASE, user_one._id)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404


@pytest.mark.django_db
class TestUserUpdate:

    @pytest.fixture()
    def user_one(self):
        user_one = AuthUserFactory.build(
            fullname='Martin Luther King Jr.',
            given_name='Martin',
            family_name='King',
            suffix='Jr.',
            social=dict(
                github='userOneGithub',
                scholar='userOneScholar',
                profileWebsites=['http://www.useronepersonalwebsite.com'],
                twitter='userOneTwitter',
                linkedIn='userOneLinkedIn',
                impactStory='userOneImpactStory',
                orcid='userOneOrcid',
                researcherId='userOneResearcherId'
            )
        )
        user_one.save()
        return user_one

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def region(self):
        return RegionFactory(name='Frankfort', _id='eu-central-1')

    @pytest.fixture()
    def region_payload(self, user_one, region):
        return {
            'data': {
                'type': 'users',
                'id': user_one._id,
                'relationships': {
                    'default_region': {
                        'data': {
                            'type': 'regions',
                            'id': region._id
                        }
                    }
                }
            }
        }

    @pytest.fixture()
    def url_user_one(self, user_one):
        return '/v2/users/{}/'.format(user_one._id)

    @pytest.fixture()
    def data_new_user_one(self, user_one):
        return {
            'data': {
                'type': 'users',
                'id': user_one._id,
                'attributes': {
                    'full_name': 'el-Hajj Malik el-Shabazz',
                    'given_name': 'Malcolm',
                    'middle_names': 'Malik el-Shabazz',
                    'family_name': 'X',
                    'suffix': 'Sr.',
                    'social': {
                        'github': ['http://github.com/even_newer_github/'],
                        'scholar': 'http://scholar.google.com/citations?user=newScholar',
                        'profileWebsites': ['http://www.newpersonalwebsite.com'],
                        'twitter': ['http://twitter.com/newtwitter'],
                        'linkedIn': ['https://www.linkedin.com/newLinkedIn'],
                        'impactStory': 'https://impactstory.org/newImpactStory',
                        'orcid': 'http://orcid.org/newOrcid',
                        'researcherId': 'http://researcherid.com/rid/newResearcherId',
                    }},
            }}

    @pytest.fixture()
    def data_missing_id(self):
        return {
            'data': {
                'type': 'users',
                'attributes': {
                    'full_name': 'el-Hajj Malik el-Shabazz',
                    'family_name': 'Z',
                }
            }
        }

    @pytest.fixture()
    def data_missing_type(self, user_one):
        return {
            'data': {
                'id': user_one._id,
                'attributes': {
                    'fullname': 'el-Hajj Malik el-Shabazz',
                    'family_name': 'Z',
                }
            }
        }

    @pytest.fixture()
    def data_incorrect_id(self):
        return {
            'data': {
                'id': '12345',
                'type': 'users',
                'attributes': {
                    'full_name': 'el-Hajj Malik el-Shabazz',
                    'family_name': 'Z',
                }
            }
        }

    @pytest.fixture()
    def data_incorrect_type(self, user_one):
        return {
            'data': {
                'id': user_one._id,
                'type': 'Wrong type.',
                'attributes': {
                    'full_name': 'el-Hajj Malik el-Shabazz',
                    'family_name': 'Z',
                }
            }
        }

    @pytest.fixture()
    def data_blank_but_not_empty_full_name(self, user_one):
        return {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'full_name': ' '
                }

            }
        }

    def test_select_for_update(
            self, app, user_one, url_user_one, data_new_user_one):
        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            res = app.patch_json_api(url_user_one, {
                'data': {
                    'id': user_one._id,
                    'type': 'users',
                    'attributes': {
                        'family_name': data_new_user_one['data']['attributes']['family_name'],
                    }
                }
            }, auth=user_one.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['family_name'] == data_new_user_one['data']['attributes']['family_name']

        for_update_sql = connection.ops.for_update_sql()
        assert any(for_update_sql in query['sql']
                   for query in ctx.captured_queries)

    @mock.patch('osf.utils.requests.settings.SELECT_FOR_UPDATE_ENABLED', False)
    def test_select_for_update_disabled(
            self, app, user_one, url_user_one, data_new_user_one):
        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            res = app.patch_json_api(url_user_one, {
                'data': {
                    'id': user_one._id,
                    'type': 'users',
                    'attributes': {
                        'family_name': data_new_user_one['data']['attributes']['family_name'],
                    }
                }
            }, auth=user_one.auth)

        assert res.status_code == 200
        assert res.json['data']['attributes']['family_name'] == data_new_user_one['data']['attributes']['family_name']

        for_update_sql = connection.ops.for_update_sql()
        assert not any(for_update_sql in query['sql']
                       for query in ctx.captured_queries)

    def test_patch_user_default_region(self, app, user_one, user_two, region, region_payload, url_user_one):
        original_user_region = user_one.osfstorage_region

        # Unauthenticated user updating region
        res = app.patch_json_api(
            url_user_one,
            region_payload,
            expect_errors=True
        )
        assert res.status_code == 401

        # Different user updating region
        res = app.patch_json_api(
            url_user_one,
            region_payload,
            auth=user_two.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        # User updating own region
        res = app.patch_json_api(
            url_user_one,
            region_payload,
            auth=user_one.auth
        )
        assert res.status_code == 200
        assert user_one.osfstorage_region == region
        assert user_one.osfstorage_region != original_user_region
        assert res.json['data']['relationships']['default_region']['data']['id'] == region._id
        assert res.json['data']['relationships']['default_region']['data']['type'] == 'regions'

        # Updating with invalid region
        region_payload['data']['relationships']['default_region']['data']['id'] = 'bad_region'
        res = app.patch_json_api(
            url_user_one,
            region_payload,
            auth=user_one.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Region bad_region is invalid.'

    def test_update_patch_errors(
            self, app, user_one, user_two, data_new_user_one,
            data_incorrect_type, data_incorrect_id,
            data_missing_type, data_missing_id,
            data_blank_but_not_empty_full_name, url_user_one):

        #   test_update_user_blank_but_not_empty_full_name
        res = app.put_json_api(
            url_user_one,
            data_blank_but_not_empty_full_name,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be blank.'

    #   test_partial_update_user_blank_but_not_empty_full_name
        res = app.patch_json_api(
            url_user_one,
            data_blank_but_not_empty_full_name,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be blank.'

    #   test_patch_user_incorrect_type
        res = app.put_json_api(
            url_user_one,
            data_incorrect_type,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 409

    #   test_patch_user_incorrect_id
        res = app.put_json_api(
            url_user_one,
            data_incorrect_id,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 409

    #   test_patch_user_no_type
        res = app.put_json_api(
            url_user_one,
            data_missing_type,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'

    #   test_patch_user_no_id
        res = app.put_json_api(
            url_user_one,
            data_missing_id,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be null.'

    #   test_partial_patch_user_incorrect_type
        res = app.patch_json_api(
            url_user_one,
            data_incorrect_type,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 409

    #   test_partial_patch_user_incorrect_id
        res = app.patch_json_api(
            url_user_one,
            data_incorrect_id,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 409

    #   test_partial_patch_user_no_type
        res = app.patch_json_api(
            url_user_one,
            data_missing_type,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400

    #   test_partial_patch_user_no_id
        res = app.patch_json_api(
            url_user_one,
            data_missing_id,
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400

    #   test_patch_fields_not_nested
        res = app.put_json_api(
            url_user_one,
            {
                'data': {
                    'id': user_one._id,
                    'type': 'users',
                    'full_name': 'New name'
                }
            },
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field is required.'

    #   test_partial_patch_fields_not_nested
        res = app.patch_json_api(
            url_user_one,
            {
                'data': {
                    'id': user_one._id,
                    'type': 'users',
                    'full_name': 'New name'
                }
            },
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 200

    #   test_patch_user_logged_out
        res = app.patch_json_api(url_user_one, {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'full_name': data_new_user_one['data']['attributes']['full_name'],
                }
            }
        }, expect_errors=True)
        assert res.status_code == 401

    #   test_put_user_without_required_field
        # PUT requires all required fields
        res = app.put_json_api(url_user_one, {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'family_name': data_new_user_one['data']['attributes']['family_name'],
                }
            }
        }, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400

    #   test_put_user_logged_out
        res = app.put_json_api(
            url_user_one,
            data_new_user_one,
            expect_errors=True)
        assert res.status_code == 401

    #   test_put_wrong_user
        # User tries to update someone else's user information via put
        res = app.put_json_api(
            url_user_one,
            data_new_user_one,
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_patch_wrong_user
        # User tries to update someone else's user information via patch
        res = app.patch_json_api(url_user_one, {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'full_name': data_new_user_one['data']['attributes']['full_name'],
                }
            }
        }, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        user_one.reload()
        assert user_one.fullname != data_new_user_one['data']['attributes']['full_name']

    #   test_update_user_social_with_invalid_value
        """update the social key which is not profileWebsites with more than one value should throw an error"""
        original_github = user_one.social['github']
        res = app.patch_json_api(url_user_one, {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'full_name': 'new_fullname',
                    'suffix': 'The Millionth',
                    'social': {
                        'github': ['even_newer_github', 'bad_github'],
                    }
                },
            }
        }, auth=user_one.auth, expect_errors=True)
        user_one.reload()
        assert res.status_code == 400
        assert user_one.social['github'] == original_github

        # Test list with non-string value
        res = app.patch_json_api(url_user_one, {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'social': {
                        'github': [{'should': 'not_work'}]
                    }
                }
            }
        }, auth=user_one.auth, expect_errors=True)
        user_one.reload()
        assert res.status_code == 400
        assert user_one.social['github'] == original_github

    def test_patch_user_without_required_field(
            self, app, user_one, data_new_user_one, url_user_one):
        # PATCH does not require required fields
        res = app.patch_json_api(url_user_one, {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'family_name': data_new_user_one['data']['attributes']['family_name'],
                }
            }
        }, auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['family_name'] == data_new_user_one['data']['attributes']['family_name']
        user_one.reload()
        assert user_one.family_name == data_new_user_one['data']['attributes']['family_name']

    def test_partial_patch_user_logged_in(self, app, user_one, url_user_one):
        # Test to make sure new fields are patched and old fields stay the same
        res = app.patch_json_api(url_user_one, {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'full_name': 'new_fullname',
                    'suffix': 'The Millionth',
                    'social': {
                        'github': ['even_newer_github'],
                    }
                },

            }}, auth=user_one.auth)
        user_one.reload()
        assert res.status_code == 200
        assert res.json['data']['attributes']['full_name'] == 'new_fullname'
        assert res.json['data']['attributes']['suffix'] == 'The Millionth'
        social = res.json['data']['attributes']['social']
        assert 'even_newer_github' in social['github'][0]
        assert res.json['data']['attributes']['given_name'] == user_one.given_name
        assert res.json['data']['attributes']['middle_names'] == user_one.middle_names
        assert res.json['data']['attributes']['family_name'] == user_one.family_name
        assert user_one.social['profileWebsites'] == social['profileWebsites']
        assert user_one.social['twitter'] in social['twitter']
        assert user_one.social['linkedIn'] in social['linkedIn']
        assert user_one.social['impactStory'] in social['impactStory']
        assert user_one.social['orcid'] in social['orcid']
        assert user_one.social['researcherId'] in social['researcherId']
        assert user_one.fullname == 'new_fullname'
        assert user_one.suffix == 'The Millionth'
        assert user_one.social['github'] == ['even_newer_github']

    def test_patch_all_social_fields(self, app, user_one, url_user_one, mock_spam_head_request):
        social_payload = {
            'github': ['the_coolest_coder'],
            'scholar': 'neat',
            'profileWebsites': ['http://yeah.com', 'http://cool.com'],
            'baiduScholar': 'ok',
            'twitter': ['tweetmaster'],
            'linkedIn': ['networkingmaster'],
            'academiaProfileID': 'okokokok',
            'ssrn': 'aaaa',
            'impactStory': 'why not',
            'orcid': 'ork-id',
            'researchGate': 'Why are there so many of these',
            'researcherId': 'ok-lastone'
        }

        fake_fields = {
            'nope': ['notreal'],
            'totallyNot': {
                'a': ['thing']
            }
        }

        # Payload with fields not in the schema should fail
        new_fields = social_payload.copy()
        new_fields.update(fake_fields)
        res = app.patch_json_api(url_user_one, {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'social': new_fields
                }
            }
        }, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert 'Additional properties are not allowed' in res.json['errors'][0]['detail']

        # Payload only containing fields in schema are OK
        res = app.patch_json_api(url_user_one, {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'social': social_payload
                }
            }
        }, auth=user_one.auth)

        user_one.reload()
        for key, value in res.json['data']['attributes']['social'].items():
            assert user_one.social[key] == value == social_payload[key]

    def test_partial_patch_user_logged_in_no_social_fields(
            self, app, user_one, url_user_one):
        # Test to make sure new fields are patched and old fields stay the same
        res = app.patch_json_api(url_user_one, {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'full_name': 'new_fullname',
                    'suffix': 'The Millionth',
                    'social': {
                        'github': ['even_newer_github'],
                    }
                },
            }
        }, auth=user_one.auth)
        user_one.reload()
        assert res.status_code == 200
        assert res.json['data']['attributes']['full_name'] == 'new_fullname'
        assert res.json['data']['attributes']['suffix'] == 'The Millionth'
        social = res.json['data']['attributes']['social']
        assert user_one.social['github'][0] in social['github']
        assert res.json['data']['attributes']['given_name'] == user_one.given_name
        assert res.json['data']['attributes']['middle_names'] == user_one.middle_names
        assert res.json['data']['attributes']['family_name'] == user_one.family_name
        assert user_one.social['profileWebsites'] == social['profileWebsites']
        assert user_one.social['twitter'] in social['twitter']
        assert user_one.social['linkedIn'] in social['linkedIn']
        assert user_one.social['impactStory'] in social['impactStory']
        assert user_one.social['orcid'] in social['orcid']
        assert user_one.social['researcherId'] in social['researcherId']
        assert user_one.fullname == 'new_fullname'
        assert user_one.suffix == 'The Millionth'
        assert user_one.social['github'] == user_one.social['github']

    def test_partial_put_user_logged_in(self, app, user_one, url_user_one):
        # Test to make sure new fields are patched and old fields stay the same
        res = app.put_json_api(url_user_one, {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'full_name': 'new_fullname',
                    'suffix': 'The Millionth',
                    'social': {
                        'github': ['even_newer_github'],
                    }
                },
            }
        }, auth=user_one.auth)
        user_one.reload()
        assert res.status_code == 200
        assert res.json['data']['attributes']['full_name'] == 'new_fullname'
        assert res.json['data']['attributes']['suffix'] == 'The Millionth'
        assert 'even_newer_github' in res.json['data']['attributes']['social']['github']
        assert res.json['data']['attributes']['given_name'] == user_one.given_name
        assert res.json['data']['attributes']['middle_names'] == user_one.middle_names
        assert res.json['data']['attributes']['family_name'] == user_one.family_name
        assert user_one.fullname == 'new_fullname'
        assert user_one.suffix == 'The Millionth'
        assert user_one.social['github'] == ['even_newer_github']

    def test_put_user_logged_in(self, app, user_one, data_new_user_one, url_user_one):
        # Logged in user updates their user information via put
        res = app.put_json_api(
            url_user_one,
            data_new_user_one,
            auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['full_name'] == data_new_user_one['data']['attributes']['full_name']
        assert res.json['data']['attributes']['given_name'] == data_new_user_one['data']['attributes']['given_name']
        assert res.json['data']['attributes']['middle_names'] == data_new_user_one['data']['attributes']['middle_names']
        assert res.json['data']['attributes']['family_name'] == data_new_user_one['data']['attributes']['family_name']
        assert res.json['data']['attributes']['suffix'] == data_new_user_one['data']['attributes']['suffix']
        social = res.json['data']['attributes']['social']
        assert 'even_newer_github' in social['github'][0]
        assert 'http://www.newpersonalwebsite.com' in social['profileWebsites'][0]
        assert 'newtwitter' in social['twitter'][0]
        assert 'newLinkedIn' in social['linkedIn'][0]
        assert 'newImpactStory' in social['impactStory']
        assert 'newOrcid' in social['orcid']
        assert 'newResearcherId' in social['researcherId']
        user_one.reload()
        assert user_one.fullname == data_new_user_one['data']['attributes']['full_name']
        assert user_one.given_name == data_new_user_one['data']['attributes']['given_name']
        assert user_one.middle_names == data_new_user_one['data']['attributes']['middle_names']
        assert user_one.family_name == data_new_user_one['data']['attributes']['family_name']
        assert user_one.suffix == data_new_user_one['data']['attributes']['suffix']
        assert 'even_newer_github' in social['github'][0]
        assert 'http://www.newpersonalwebsite.com' in social['profileWebsites'][0]
        assert 'newtwitter' in social['twitter'][0]
        assert 'newLinkedIn' in social['linkedIn'][0]
        assert 'newImpactStory' in social['impactStory']
        assert 'newOrcid' in social['orcid']
        assert 'newResearcherId' in social['researcherId']

    def test_update_user_sanitizes_html_properly(
            self, app, user_one, url_user_one):
        """Post request should update resource, and any HTML in fields should be stripped"""
        bad_fullname = 'Malcolm <strong>X</strong>'
        bad_family_name = 'X <script>alert("is")</script> a cool name'
        res = app.patch_json_api(url_user_one, {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'full_name': bad_fullname,
                    'family_name': bad_family_name,
                }
            }
        }, auth=user_one.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['full_name'] == strip_html(
            bad_fullname)
        assert res.json['data']['attributes']['family_name'] == strip_html(
            bad_family_name)

    def test_update_accepted_tos_sets_field(
            self, app, user_one, url_user_one):
        assert user_one.accepted_terms_of_service is None
        res = app.patch_json_api(
            url_user_one,
            {
                'data': {
                    'id': user_one._id,
                    'type': 'users',
                    'attributes': {
                        'accepted_terms_of_service': True,
                    }
                }
            },
            auth=user_one.auth
        )
        user_one.reload()
        assert res.status_code == 200
        assert user_one.accepted_terms_of_service is not None
        assert isinstance(user_one.accepted_terms_of_service, dt.datetime)

    def test_update_accepted_tos_false(
            self, app, user_one, url_user_one):
        assert user_one.accepted_terms_of_service is None
        res = app.patch_json_api(
            url_user_one,
            {
                'data': {
                    'id': user_one._id,
                    'type': 'users',
                    'attributes': {
                        'accepted_terms_of_service': False,
                    }
                }
            },
            auth=user_one.auth
        )
        user_one.reload()
        assert res.status_code == 200
        assert user_one.accepted_terms_of_service is None

    def test_update_allow_indexing_sets_field(
            self, app, user_one, url_user_one):
        assert user_one.allow_indexing is None
        res = app.patch_json_api(
            url_user_one,
            {
                'data': {
                    'id': user_one._id,
                    'type': 'users',
                    'attributes': {
                        'allow_indexing': True,
                    }
                }
            },
            auth=user_one.auth
        )
        user_one.reload()
        assert res.status_code == 200
        assert user_one.allow_indexing is True
        res = app.patch_json_api(
            url_user_one,
            {
                'data': {
                    'id': user_one._id,
                    'type': 'users',
                    'attributes': {
                        'allow_indexing': False,
                    }
                }
            },
            auth=user_one.auth
        )
        user_one.reload()
        assert res.status_code == 200
        assert user_one.allow_indexing is False


@pytest.mark.django_db
class TestDeactivatedUser:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    def test_requesting_as_deactivated_user_returns_400_response(
            self, app, user_one):
        url = '/{}users/{}/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 200
        user_one.is_disabled = True
        user_one.save()
        res = app.get(url, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Making API requests with credentials associated with a deactivated account is not allowed.'

    def test_unconfirmed_users_return_entire_user_object(
            self, app, user_one, user_two):
        url = '/{}users/{}/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 200
        user_one.is_registered = False
        user_one.save()
        res = app.get(url, expect_errors=True)
        assert res.status_code == 200
        attr = res.json['data']['attributes']
        assert attr['active'] is False
        assert res.json['data']['id'] == user_one._id

    def test_requesting_deactivated_user_returns_410_response_and_meta_info(
            self, app, user_one, user_two):
        url = '/{}users/{}/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 200
        user_one.is_disabled = True
        user_one.save()
        res = app.get(url, expect_errors=True)
        assert res.status_code == 410
        assert res.json['errors'][0]['meta']['family_name'] == user_one.family_name
        assert res.json['errors'][0]['meta']['given_name'] == user_one.given_name
        assert res.json['errors'][0]['meta']['middle_names'] == user_one.middle_names
        assert res.json['errors'][0]['meta']['full_name'] == user_one.fullname
        assert urlparse(
            res.json['errors'][0]['meta']['profile_image']).netloc == 'secure.gravatar.com'
        assert res.json['errors'][0]['detail'] == 'The requested user is no longer available.'


@pytest.mark.django_db
class UserProfileMixin(object):

    @pytest.fixture()
    def request_payload(self):
        raise NotImplementedError

    @pytest.fixture()
    def bad_request_payload(self, request_payload, request_key):
        request_payload['data']['attributes'][request_key][0]['bad_key'] = 'bad_value'
        return request_payload

    @pytest.fixture()
    def end_dates_no_start_dates_payload(self, request_payload, request_key):
        del request_payload['data']['attributes'][request_key][0]['startYear']
        del request_payload['data']['attributes'][request_key][0]['startMonth']
        return request_payload

    @pytest.fixture()
    def start_dates_no_end_dates_payload(self, request_payload, request_key):
        request_payload['data']['attributes'][request_key][0]['ongoing'] = True
        del request_payload['data']['attributes'][request_key][0]['endYear']
        del request_payload['data']['attributes'][request_key][0]['endMonth']
        return request_payload

    @pytest.fixture()
    def end_month_dependency_payload(self, request_payload, request_key):
        del request_payload['data']['attributes'][request_key][0]['endYear']
        return request_payload

    @pytest.fixture()
    def start_month_dependency_payload(self, request_payload, request_key):
        del request_payload['data']['attributes'][request_key][0]['startYear']
        return request_payload

    @pytest.fixture()
    def request_key(self):
        raise NotImplementedError

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_one_url(self, user_one):
        return '/v2/users/{}/'.format(user_one._id)

    @mock.patch('osf.models.user.OSFUser.check_spam')
    def test_user_put_profile_200(self, mock_check_spam, app, user_one, user_one_url, request_payload, request_key, user_attr):
        res = app.put_json_api(user_one_url, request_payload, auth=user_one.auth)
        user_one.reload()
        assert res.status_code == 200
        assert getattr(user_one, user_attr) == request_payload['data']['attributes'][request_key]
        assert mock_check_spam.called

    def test_user_put_profile_400(self, app, user_one, user_one_url, bad_request_payload):
        res = app.put_json_api(user_one_url, bad_request_payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == "Additional properties are not allowed ('bad_key' was unexpected)"

    def test_user_put_profile_401(self, app, user_one, user_one_url, request_payload):
        res = app.put_json_api(user_one_url, request_payload, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == 'Authentication credentials were not provided.'

    def test_user_put_profile_403(self, app, user_two, user_one_url, request_payload):
        res = app.put_json_api(user_one_url, request_payload, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    def test_user_put_profile_validate_dict(self, app, user_one, user_one_url, request_payload, request_key):
        # Tests to make sure profile's fields have correct structure
        request_payload['data']['attributes'][request_key] = {}
        res = app.put_json_api(user_one_url, request_payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Expected a list of items but got type "dict".'

    def test_user_put_profile_validation_list(self, app, user_one, user_one_url, request_payload, request_key):
        # Tests to make sure structure is lists of dicts consisting of proper fields
        request_payload['data']['attributes'][request_key] = [{}]
        res = app.put_json_api(user_one_url, request_payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == "'institution' is a required property"

    def test_user_put_profile_validation_empty_string(self, app, user_one, user_one_url, request_payload, request_key):
        # Tests to make sure institution is not empty string
        request_payload['data']['attributes'][request_key][0]['institution'] = ''
        res = app.put_json_api(user_one_url, request_payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == "For 'institution' the field value '' is too short"

    def test_user_put_profile_validation_start_year_dependency(self, app, user_one, user_one_url, request_payload, request_key):
        # Tests to make sure ongoing is bool
        del request_payload['data']['attributes'][request_key][0]['ongoing']
        res = app.put_json_api(user_one_url, request_payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == "'ongoing' is a dependency of 'startYear'"

    def test_user_put_profile_date_validate_int(self, app, user_one, user_one_url, request_payload, request_key):
        # Not valid datatypes for dates

        request_payload['data']['attributes'][request_key][0]['startYear'] = 'string'
        res = app.put_json_api(user_one_url, request_payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == "For 'startYear' the field value 'string' is not of type 'integer'"

    def test_user_put_profile_date_validate_positive(self, app, user_one, user_one_url, request_payload, request_key):
        # Not valid values for dates
        request_payload['data']['attributes'][request_key][0]['startYear'] = -2
        res = app.put_json_api(user_one_url, request_payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == "For 'startYear' the field value -2 is less than the minimum of 1900"

    def test_user_put_profile_date_validate_ongoing_position(self, app, user_one, user_one_url, request_payload, request_key):
        # endDates for ongoing position
        request_payload['data']['attributes'][request_key][0]['ongoing'] = True
        del request_payload['data']['attributes'][request_key][0]['endYear']
        res = app.put_json_api(user_one_url, request_payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400

    def test_user_put_profile_date_validate_end_date(self, app, user_one, user_one_url, request_payload, request_key):
        # End date is greater then start date
        request_payload['data']['attributes'][request_key][0]['startYear'] = 2000
        res = app.put_json_api(user_one_url, request_payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'End date must be greater than or equal to the start date.'

    def test_user_put_profile_date_validate_end_month_dependency(self, app, user_one, user_one_url, end_month_dependency_payload):
        # No endMonth with endYear
        res = app.put_json_api(user_one_url, end_month_dependency_payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == "'endYear' is a dependency of 'endMonth'"

    def test_user_put_profile_date_validate_start_month_dependency(self, app, user_one, user_one_url, start_month_dependency_payload):
        # No endMonth with endYear
        res = app.put_json_api(user_one_url, start_month_dependency_payload, auth=user_one.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == "'startYear' is a dependency of 'startMonth'"

    def test_user_put_profile_date_validate_start_date_no_end_date_not_ongoing(self, app, user_one, user_attr, user_one_url, start_dates_no_end_dates_payload, request_key):
        # End date is greater then start date
        res = app.put_json_api(user_one_url, start_dates_no_end_dates_payload, auth=user_one.auth, expect_errors=True)
        user_one.reload()
        assert res.status_code == 400

    def test_user_put_profile_date_validate_end_date_no_start_date(self, app, user_one, user_attr, user_one_url, end_dates_no_start_dates_payload, request_key):
        # End dates, but no start dates
        res = app.put_json_api(user_one_url, end_dates_no_start_dates_payload, auth=user_one.auth, expect_errors=True)
        user_one.reload()
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == "'startYear' is a dependency of 'endYear'"


@pytest.mark.django_db
class TestUserSchools(UserProfileMixin):

    @pytest.fixture()
    def request_payload(self, user_one):
        return {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'full_name': user_one.fullname,
                    'education': [{'degree': '',
                                   'startYear': 1991,
                                   'startMonth': 9,
                                   'endYear': 1992,
                                   'endMonth': 9,
                                   'ongoing': False,
                                   'department': '',
                                   'institution': 'Fake U'
                                   }]
                }
            }
        }

    @pytest.fixture()
    def request_key(self):
        return 'education'

    @pytest.fixture()
    def user_attr(self):
        return 'schools'


@pytest.mark.django_db
class TestUserJobs(UserProfileMixin):

    @pytest.fixture()
    def request_payload(self, user_one):
        return {
            'data': {
                'id': user_one._id,
                'type': 'users',
                'attributes': {
                    'full_name': user_one.fullname,
                    'employment': [{'title': '',
                                   'startYear': 1991,
                                   'startMonth': 9,
                                   'endYear': 1992,
                                   'endMonth': 9,
                                   'ongoing': False,
                                   'department': '',
                                   'institution': 'Fake U'
                                    }]
                }
            }
        }

    @pytest.fixture()
    def request_key(self):
        return 'employment'

    @pytest.fixture()
    def user_attr(self):
        return 'jobs'
