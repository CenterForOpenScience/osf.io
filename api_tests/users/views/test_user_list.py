# -*- coding: utf-8 -*-
import itsdangerous
import mock
import pytest
import unittest
from future.moves.urllib.parse import urlparse, parse_qs
from uuid import UUID

from api.base.settings.defaults import API_BASE
from framework.auth.cas import CasResponse
from osf.models import OSFUser, Session, ApiOAuth2PersonalToken
from osf_tests.factories import (
    AuthUserFactory,
    UserFactory,
    OSFGroupFactory,
    ProjectFactory,
    ApiOAuth2ScopeFactory,
    RegistrationFactory,
    Auth,
)
from osf.utils.permissions import CREATOR_PERMISSIONS
from website import settings


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestUsers:

    @pytest.fixture()
    def user_one(self):
        return AuthUserFactory(fullname='Freddie Mercury I')

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory(fullname='Freddie Mercury II')

    def test_returns_200(self, app):
        res = app.get('/{}users/'.format(API_BASE))
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    def test_find_user_in_users(self, app, user_one, user_two):
        url = '/{}users/'.format(API_BASE)

        res = app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert user_two._id in ids

    def test_all_users_in_users(self, app, user_one, user_two):
        url = '/{}users/'.format(API_BASE)

        res = app.get(url)
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert user_one._id in ids
        assert user_two._id in ids

    def test_merged_user_is_not_in_user_list_after_2point3(
            self, app, user_one, user_two):
        user_two.merge_user(user_one)
        res = app.get('/{}users/?version=2.3'.format(API_BASE))
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert res.status_code == 200
        assert user_two._id in ids
        assert user_one._id not in ids

    def test_merged_user_is_returned_before_2point3(
            self, app, user_one, user_two):
        user_two.merge_user(user_one)
        res = app.get('/{}users/'.format(API_BASE))
        user_son = res.json['data']

        ids = [each['id'] for each in user_son]
        assert res.status_code == 200
        assert user_two._id in ids
        assert user_one._id in ids

    def test_find_multiple_in_users(self, app, user_one, user_two):
        url = '/{}users/?filter[full_name]=fred'.format(API_BASE)

        res = app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert user_one._id in ids
        assert user_two._id in ids

    def test_find_single_user_in_users(self, app, user_one, user_two):
        url = '/{}users/?filter[full_name]=my'.format(API_BASE)
        user_one.fullname = 'My Mom'
        user_one.save()
        res = app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert user_one._id in ids
        assert user_two._id not in ids

    def test_find_no_user_in_users(self, app, user_one, user_two):
        url = '/{}users/?filter[full_name]=NotMyMom'.format(API_BASE)
        res = app.get(url)
        user_json = res.json['data']
        ids = [each['id'] for each in user_json]
        assert user_one._id not in ids
        assert user_two._id not in ids

    def test_more_than_one_projects_in_common(self, app, user_one, user_two):
        group = OSFGroupFactory(creator=user_one)
        group.make_member(user_two)

        project1 = ProjectFactory(creator=user_one)
        project1.add_contributor(
            contributor=user_two,
            permissions=CREATOR_PERMISSIONS,
            auth=Auth(user=user_one)
        )
        project1.save()
        project2 = ProjectFactory(creator=user_one)
        project2.add_contributor(
            contributor=user_two,
            permissions=CREATOR_PERMISSIONS,
            auth=Auth(user=user_one)
        )
        project2.save()

        project3 = ProjectFactory()
        project4 = ProjectFactory()
        project3.add_osf_group(group)
        project4.add_osf_group(group)
        project4.is_deleted = True
        project3.save()
        project4.save()

        RegistrationFactory(
            project=project1,
            creator=user_one,
            is_public=True)

        url = '/{}users/?show_projects_in_common=true'.format(API_BASE)
        res = app.get(url, auth=user_two.auth)
        user_json = res.json['data']
        for user in user_json:
            if user['id'] == user_two._id:
                meta = user['relationships']['nodes']['links']['related']['meta']
                assert 'projects_in_common' in meta
                assert meta['projects_in_common'] == 4

    def test_users_projects_in_common(self, app, user_one, user_two):
        user_one.fullname = 'hello'
        user_one.save()
        url = '/{}users/?show_projects_in_common=true'.format(API_BASE)
        res = app.get(url, auth=user_two.auth)
        user_json = res.json['data']
        for user in user_json:
            meta = user['relationships']['nodes']['links']['related']['meta']
            assert 'projects_in_common' in meta
            assert meta['projects_in_common'] == 0

    def test_users_projects_in_common_with_embed_and_right_query(
            self, app, user_one, user_two):
        project = ProjectFactory(creator=user_one)
        project.add_contributor(
            contributor=user_two,
            permissions=CREATOR_PERMISSIONS,
            auth=Auth(user=user_one)
        )
        project.save()
        url = '/{}users/{}/nodes/?embed=contributors&show_projects_in_common=true'.format(
            API_BASE, user_two._id)
        res = app.get(url, auth=user_two.auth)
        user_json = res.json['data'][0]['embeds']['contributors']['data']
        for user in user_json:
            meta = user['embeds']['users']['data']['relationships']['nodes']['links']['related']['meta']
            assert 'projects_in_common' in meta
            assert meta['projects_in_common'] == 1

    def test_users_projects_in_common_exclude_deleted_projects(
            self, app, user_one, user_two):
        project_list = []
        for x in range(1, 10):
            project = ProjectFactory(creator=user_one)
            project.add_contributor(
                contributor=user_two,
                permissions=CREATOR_PERMISSIONS,
                auth=Auth(user=user_one)
            )
            project.save()
            project_list.append(project)
        for x in range(1, 5):
            project = project_list[x]
            project.reload()
            project.remove_node(auth=Auth(user=user_one))
        url = '/{}users/{}/nodes/?embed=contributors&show_projects_in_common=true'.format(
            API_BASE, user_two._id)
        res = app.get(url, auth=user_two.auth)
        user_json = res.json['data'][0]['embeds']['contributors']['data']
        for user in user_json:
            meta = user['embeds']['users']['data']['relationships']['nodes']['links']['related']['meta']
            assert 'projects_in_common' in meta
            assert meta['projects_in_common'] == 5

    def test_users_projects_in_common_with_embed_without_right_query(
            self, app, user_one, user_two):
        project = ProjectFactory(creator=user_one)
        project.add_contributor(
            contributor=user_two,
            permissions=CREATOR_PERMISSIONS,
            auth=Auth(user=user_one)
        )
        project.save()
        url = '/{}users/{}/nodes/?embed=contributors'.format(
            API_BASE, user_two._id)
        res = app.get(url, auth=user_two.auth)
        user_json = res.json['data'][0]['embeds']['contributors']['data']
        for user in user_json:
            meta = user['embeds']['users']['data']['relationships']['nodes']['links']['related']['meta']
            assert 'projects_in_common' not in meta

    def test_users_no_projects_in_common_with_wrong_query(
            self, app, user_one, user_two):
        user_one.fullname = 'hello'
        user_one.save()
        url = '/{}users/?filter[full_name]={}'.format(
            API_BASE, user_one.fullname)
        res = app.get(url, auth=user_two.auth)
        user_json = res.json['data']
        for user in user_json:
            meta = user['relationships']['nodes']['links']['related']['meta']
            assert 'projects_in_common' not in meta

    def test_users_no_projects_in_common_without_filter(
            self, app, user_one, user_two):
        user_one.fullname = 'hello'
        user_one.save()
        url = '/{}users/'.format(API_BASE)
        res = app.get(url, auth=user_two.auth)
        user_json = res.json['data']
        for user in user_json:
            meta = user['relationships']['nodes']['links']['related']['meta']
            assert 'projects_in_common' not in meta

    def test_users_list_takes_profile_image_size_param(
            self, app, user_one, user_two):
        size = 42
        url = '/{}users/?profile_image_size={}'.format(API_BASE, size)
        res = app.get(url)
        user_json = res.json['data']
        for user in user_json:
            profile_image_url = user['links']['profile_image']
            query_dict = parse_qs(
                urlparse(profile_image_url).query)
            assert int(query_dict.get('s')[0]) == size

    def test_users_list_filter_multiple_field(self, app, user_one, user_two):
        john_doe = UserFactory(fullname='John Doe')
        john_doe.given_name = 'John'
        john_doe.family_name = 'Doe'
        john_doe.save()

        doe_jane = UserFactory(fullname='Doe Jane')
        doe_jane.given_name = 'Doe'
        doe_jane.family_name = 'Jane'
        doe_jane.save()

        url = '/{}users/?filter[given_name,family_name]=Doe'.format(API_BASE)
        res = app.get(url)
        data = res.json['data']
        assert len(data) == 2

    def test_users_list_filter_multiple_fields_with_additional_filters(
            self, app, user_one, user_two):
        john_doe = UserFactory(fullname='John Doe')
        john_doe.given_name = 'John'
        john_doe.family_name = 'Doe'
        john_doe.save()

        doe_jane = UserFactory(fullname='Doe Jane')
        doe_jane.given_name = 'Doe'
        doe_jane.family_name = 'Jane'
        doe_jane.save()

        url = '/{}users/?filter[given_name,family_name]=Doe&filter[id]={}'.format(
            API_BASE, john_doe._id)
        res = app.get(url)
        data = res.json['data']
        assert len(data) == 1

    def test_users_list_filter_multiple_fields_with_bad_filter(
            self, app, user_one, user_two):
        url = '/{}users/?filter[given_name,not_a_filter]=Doe'.format(API_BASE)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 400


@pytest.mark.django_db
class TestUsersCreate:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def email_unconfirmed(self):
        return 'tester@fake.io'

    @pytest.fixture()
    def url_base(self):
        return '/{}users/'.format(API_BASE)

    @pytest.fixture()
    def data(self, email_unconfirmed):
        return {
            'data': {
                'type': 'users',
                'attributes': {
                    'username': email_unconfirmed,
                    'full_name': 'Test Account'
                }
            }
        }

    def tearDown(self, app):
        super(TestUsersCreate, self).tearDown()
        app.reset()  # clears cookies
        OSFUser.remove()

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_logged_in_user_with_basic_auth_cannot_create_other_user_or_send_mail(
            self, mock_mail, app, user, email_unconfirmed, data, url_base):
        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 0
        res = app.post_json_api(
            '{}?send_email=true'.format(url_base),
            data,
            auth=user.auth,
            expect_errors=True
        )

        assert res.status_code == 403
        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 0
        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_logged_out_user_cannot_create_other_user_or_send_mail(
            self, mock_mail, app, email_unconfirmed, data, url_base):
        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 0
        res = app.post_json_api(
            '{}?send_email=true'.format(url_base),
            data,
            expect_errors=True
        )

        assert res.status_code == 401
        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 0
        assert mock_mail.call_count == 0

    @pytest.mark.skip  # failing locally post converision
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_cookied_requests_can_create_and_email(
            self, mock_mail, app, user, email_unconfirmed, data, url_base):
        session = Session(data={'auth_user_id': user._id})
        session.save()
        cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(session._id)
        app.set_cookie(settings.COOKIE_NAME, str(cookie))

        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 0
        res = app.post_json_api(
            '{}?send_email=true'.format(url_base),
            data
        )
        assert res.status_code == 201
        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 1
        assert mock_mail.call_count == 1

    @pytest.mark.skip  # failing locally post converision
    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    # TODO: Remove when available outside of DEV_MODE
    @unittest.skipIf(
        not settings.DEV_MODE,
        'DEV_MODE disabled, osf.users.create unavailable')
    def test_properly_scoped_token_can_create_and_send_email(
            self, mock_auth, mock_mail, app, user, email_unconfirmed, data, url_base):
        token = ApiOAuth2PersonalToken(
            owner=user,
            name='Authorized Token',
        )
        scope = ApiOAuth2ScopeFactory()
        scope.name = 'osf.users.create'
        scope.save()
        token.scopes.add(scope)

        mock_cas_resp = CasResponse(
            authenticated=True,
            user=user._id,
            attributes={
                'accessToken': token.token_id,
                'accessTokenScope': [s.name for s in token.scopes.all()]
            }
        )
        mock_auth.return_value = user, mock_cas_resp

        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 0
        res = app.post_json_api(
            '{}?send_email=true'.format(url_base),
            data,
            headers={'Authorization': 'Bearer {}'.format(token.token_id)}
        )

        assert res.status_code == 201
        assert res.json['data']['attributes']['username'] == email_unconfirmed
        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 1
        assert mock_mail.call_count == 1

    @pytest.mark.skip  # failing locally post converision
    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    # TODO: Remove when available outside of DEV_MODE
    @unittest.skipIf(
        not settings.DEV_MODE,
        'DEV_MODE disabled, osf.users.create unavailable')
    def test_properly_scoped_token_does_not_send_email_without_kwarg(
            self, mock_auth, mock_mail, app, user, email_unconfirmed, data, url_base):
        token = ApiOAuth2PersonalToken(
            owner=user,
            name='Authorized Token',

        )
        scope = ApiOAuth2ScopeFactory()
        scope.name = 'osf.users.create'
        scope.save()
        token.scopes.add(scope)

        mock_cas_resp = CasResponse(
            authenticated=True,
            user=user._id,
            attributes={
                'accessToken': token.token_id,
                'accessTokenScope': [s.name for s in token.scopes.all()]
            }
        )
        mock_auth.return_value = user, mock_cas_resp

        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 0

        res = app.post_json_api(
            url_base,
            data,
            headers={'Authorization': 'Bearer {}'.format(token.token_id)}
        )

        assert res.status_code == 201
        assert res.json['data']['attributes']['username'] == email_unconfirmed
        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 1
        assert mock_mail.call_count == 0

    @pytest.mark.skip  # failing locally post converision
    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    # TODO: Remove when available outside of DEV_MODE
    @unittest.skipIf(
        not settings.DEV_MODE,
        'DEV_MODE disabled, osf.users.create unavailable')
    def test_properly_scoped_token_can_create_without_username_but_not_send_email(
            self, mock_auth, mock_mail, app, user, data, url_base):
        token = ApiOAuth2PersonalToken(
            owner=user,
            name='Authorized Token',
        )
        scope = ApiOAuth2ScopeFactory()
        scope.name = 'osf.users.create'
        scope.save()
        token.scopes.add(scope)

        mock_cas_resp = CasResponse(
            authenticated=True,
            user=user._id,
            attributes={
                'accessToken': token.token_id,
                'accessTokenScope': [s.name for s in token.scopes.all()]
            }
        )
        mock_auth.return_value = user, mock_cas_resp

        data['data']['attributes'] = {'full_name': 'No Email'}

        assert OSFUser.objects.filter(fullname='No Email').count() == 0
        res = app.post_json_api(
            '{}?send_email=true'.format(url_base),
            data,
            headers={'Authorization': 'Bearer {}'.format(token.token_id)}
        )

        assert res.status_code == 201
        username = res.json['data']['attributes']['username']
        try:
            UUID(username)
        except ValueError:
            raise AssertionError('Username is not a valid UUID')
        assert OSFUser.objects.filter(fullname='No Email').count() == 1
        assert mock_mail.call_count == 0

    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    def test_improperly_scoped_token_can_not_create_or_email(
            self, mock_auth, mock_mail, app, user, email_unconfirmed, data, url_base):
        token = ApiOAuth2PersonalToken(
            owner=user,
            name='Unauthorized Token',
        )
        token.save()

        scope = ApiOAuth2ScopeFactory()
        scope.name = 'unauthorized scope'
        scope.save()
        token.scopes.add(scope)

        mock_cas_resp = CasResponse(
            authenticated=True,
            user=user._id,
            attributes={
                'accessToken': token.token_id,
                'accessTokenScope': [s.name for s in token.scopes.all()]
            }
        )
        mock_auth.return_value = user, mock_cas_resp

        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 0
        res = app.post_json_api(
            '{}?send_email=true'.format(url_base),
            data,
            headers={'Authorization': 'Bearer {}'.format(token.token_id)},
            expect_errors=True
        )

        assert res.status_code == 403
        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 0
        assert mock_mail.call_count == 0

    @pytest.mark.skip  # failing locally post converision
    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('api.base.authentication.drf.OSFCASAuthentication.authenticate')
    # TODO: Remove when available outside of DEV_MODE
    @unittest.skipIf(
        not settings.DEV_MODE,
        'DEV_MODE disabled, osf.admin unavailable')
    def test_admin_scoped_token_can_create_and_send_email(
            self, mock_auth, mock_mail, app, user, email_unconfirmed, data, url_base):
        token = ApiOAuth2PersonalToken(
            owner=user,
            name='Admin Token',
        )
        scope = ApiOAuth2ScopeFactory()
        scope.name = 'osf.admin'
        scope.save()
        token.scopes.add(scope)

        mock_cas_resp = CasResponse(
            authenticated=True,
            user=user._id,
            attributes={
                'accessToken': token.token_id,
                'accessTokenScope': [s.name for s in token.scopes.all()]
            }
        )
        mock_auth.return_value = user, mock_cas_resp

        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 0
        res = app.post_json_api(
            '{}?send_email=true'.format(url_base),
            data,
            headers={'Authorization': 'Bearer {}'.format(token.token_id)}
        )

        assert res.status_code == 201
        assert res.json['data']['attributes']['username'] == email_unconfirmed
        assert OSFUser.objects.filter(username=email_unconfirmed).count() == 1
        assert mock_mail.call_count == 1
