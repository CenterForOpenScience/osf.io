import pytest
import mock
import random

from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE
from api.draft_registrations.serializers import DraftRegistrationContributorsCreateSerializer
from api_tests.nodes.views.test_node_contributors_list import (
    NodeCRUDTestCase,
    TestNodeContributorList,
    TestNodeContributorAdd,
    TestNodeContributorCreateValidation,
    TestNodeContributorCreateEmail,
    TestNodeContributorBulkCreate,
    TestNodeContributorBulkUpdate,
    TestNodeContributorBulkPartialUpdate,
    TestNodeContributorBulkDelete,
    TestNodeContributorFiltering,
)
from osf_tests.factories import (
    DraftRegistrationFactory,
    AuthUserFactory,
    UserFactory,
    ProjectFactory,
)
from osf.utils import permissions
from tests.base import capture_signals
from website.project.signals import contributor_added


@pytest.fixture()
def user():
    return AuthUserFactory()

class DraftRegistrationCRUDTestCase(NodeCRUDTestCase):
    @pytest.fixture()
    def project_public(self, user, title, description, category):
        # Overrides NodeCRUDTestCase - just going to make a "public project"
        # be a draft branched from a public project.
        project = ProjectFactory(creator=user, is_public=True)
        return DraftRegistrationFactory(
            title=title,
            description=description,
            category=category,
            initiator=user,
            branched_from=project
        )

    @pytest.fixture()
    def project_private(self, user, title, description, category):
        return DraftRegistrationFactory(
            title=title,
            description=description,
            category=category,
            initiator=user
        )


class TestDraftRegistrationContributorList(DraftRegistrationCRUDTestCase, TestNodeContributorList):
    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}draft_registrations/{}/contributors/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}draft_registrations/{}/contributors/'.format(API_BASE, project_private._id)

    # Overrides TestNodeContributorList
    def test_concatenated_id(self, app, user, project_public, url_public):
        # Overriding since draft registrations can only be accessed by contribs
        res = app.get(url_public, auth=user.auth)
        assert res.status_code == 200

        assert res.json['data'][0]['id'].split('-')[0] == project_public._id
        assert res.json['data'][0]['id'] == '{}-{}'.format(
            project_public._id, user._id)

    # Overrides TestNodeContributorList
    def test_return(
            self, app, user, user_two, project_public, project_private,
            url_public, url_private, make_contrib_id):

        #   test_return_public_contributor_list_logged_in
        # Since permissions are based on the branched from node, this will not pass
        res = app.get(url_public, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403

        #   test_return_private_contributor_list_logged_out
        res = app.get(url_private, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

        #   test_return_private_contributor_list_logged_in_non_contributor
        res = app.get(url_private, auth=user_two.auth, expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    # Overrides TestNodeContributorList
    def test_return_public_contributor_list_logged_out(
            self, app, user, user_two, project_public, url_public, make_contrib_id):
        project_public.add_contributor(user_two, save=True)

        res = app.get(url_public, expect_errors=True)
        assert res.status_code == 401

    # Overrides TestNodeContributorList
    def test_disabled_contributors_contain_names_under_meta(
            self, app, user, user_two, project_public, url_public, make_contrib_id):
        project_public.add_contributor(user_two, save=True)

        user_two.is_disabled = True
        user_two.save()

        res = app.get(url_public, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 2
        assert res.json['data'][0]['id'] == make_contrib_id(
            project_public._id, user._id)
        assert res.json['data'][1]['id'] == make_contrib_id(
            project_public._id, user_two._id)
        assert res.json['data'][1]['embeds']['users']['errors'][0]['meta']['full_name'] == user_two.fullname
        assert res.json['data'][1]['embeds']['users']['errors'][0]['detail'] == 'The requested user is no longer available.'

    # Overrides TestNodeContributorList
    def test_total_bibliographic_contributor_count_returned_in_metadata(
            self, app, user_two, user, project_public, url_public):
        non_bibliographic_user = UserFactory()
        project_public.add_contributor(
            non_bibliographic_user,
            visible=False,
            auth=Auth(project_public.creator))
        project_public.save()
        res = app.get(url_public, auth=user.auth)
        assert res.status_code == 200
        assert res.json['links']['meta']['total_bibliographic'] == len(
            project_public.visible_contributor_ids)

    # Overrides TestNodeContributorList
    def test_contributors_order_is_the_same_over_multiple_requests(
            self, app, user, project_public, url_public):
        project_public.add_unregistered_contributor(
            'Robert Jackson',
            'robert@gmail.com',
            auth=Auth(user), save=True
        )

        for i in range(0, 10):
            new_user = AuthUserFactory()
            if i % 2 == 0:
                visible = True
            else:
                visible = False
            project_public.add_contributor(
                new_user,
                visible=visible,
                auth=Auth(project_public.creator),
                save=True
            )
        req_one = app.get(
            '{}?page=2'.format(url_public),
            auth=user.auth)
        req_two = app.get(
            '{}?page=2'.format(url_public),
            auth=user.auth)
        id_one = [item['id'] for item in req_one.json['data']]
        id_two = [item['id'] for item in req_two.json['data']]
        for a, b in zip(id_one, id_two):
            assert a == b

    def test_permissions_work_with_many_users(
            self, app, user, project_private, url_private):
        users = {
            permissions.ADMIN: [user._id],
            permissions.WRITE: []
        }
        for i in range(0, 25):
            perm = random.choice(list(users.keys()))
            user = AuthUserFactory()

            project_private.add_contributor(user, permissions=perm)
            users[perm].append(user._id)

        res = app.get(url_private, auth=user.auth)
        data = res.json['data']
        for user in data:
            api_perm = user['attributes']['permission']
            user_id = user['id'].split('-')[1]
            assert user_id in users[api_perm], 'Permissions incorrect for {}. Should not have {} permission.'.format(
                user_id, api_perm)


class TestDraftRegistrationContributorAdd(DraftRegistrationCRUDTestCase, TestNodeContributorAdd):
    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}draft_registrations/{}/contributors/?send_email=false'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}draft_registrations/{}/contributors/?send_email=false'.format(API_BASE, project_private._id)

    # Overrides TestNodeContributorAdd
    def test_adds_contributor_public_project_non_admin_osf_group(
            self, app, user, user_two, user_three,
            project_public, data_user_three, url_public):
        # Draft registrations don't have groups
        return

    # Overrides TestNodeContributorAdd
    def test_adds_contributor_private_project_osf_group_admin_perms(
            self, app, user, user_two, user_three, project_private,
            data_user_two, url_private):
        # Draft registrations don't have groups
        return


class TestDraftRegistrationContributorCreateValidation(DraftRegistrationCRUDTestCase, TestNodeContributorCreateValidation):

    @pytest.fixture()
    def create_serializer(self):
        # Overrides TestNodeContributorCreateValidation
        return DraftRegistrationContributorsCreateSerializer


class TestDraftContributorCreateEmail(DraftRegistrationCRUDTestCase, TestNodeContributorCreateEmail):
    @pytest.fixture()
    def url_project_contribs(self, project_public):
        # Overrides TestNodeContributorCreateEmail
        return '/{}draft_registrations/{}/contributors/'.format(API_BASE, project_public._id)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_contributor_sends_email(
            self, mock_mail, app, user, user_two,
            url_project_contribs):
        # Overrides TestNodeContributorCreateEmail
        url = '{}?send_email=draft_registration'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': user_two._id
                        }
                    }
                }
            }
        }

        res = app.post_json_api(url, payload, auth=user.auth)
        assert res.status_code == 201
        assert mock_mail.call_count == 1

    # Overrides TestNodeContributorCreateEmail
    def test_add_contributor_signal_if_default(
            self, app, user, user_two, url_project_contribs):
        url = '{}?send_email=default'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                },
                'relationships': {
                    'users': {
                        'data': {
                            'type': 'users',
                            'id': user_two._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'default is not a valid email preference.'

    # Overrides TestNodeContributorCreateEmail
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_unregistered_contributor_sends_email(
            self, mock_mail, app, user, url_project_contribs):
        url = '{}?send_email=draft_registration'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                    'email': 'kanye@west.com'
                }
            }
        }
        res = app.post_json_api(url, payload, auth=user.auth)
        assert res.status_code == 201
        assert mock_mail.call_count == 1

    # Overrides TestNodeContributorCreateEmail
    @mock.patch('website.project.signals.unreg_contributor_added.send')
    def test_add_unregistered_contributor_signal_if_default(
            self, mock_send, app, user, url_project_contribs):
        url = '{}?send_email=draft_registration'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                    'email': 'kanye@west.com'
                }
            }
        }
        res = app.post_json_api(url, payload, auth=user.auth)
        args, kwargs = mock_send.call_args
        assert res.status_code == 201
        assert 'draft_registration' == kwargs['email_template']

    # Overrides TestNodeContributorCreateEmail
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_unregistered_contributor_without_email_no_email(
            self, mock_mail, app, user, url_project_contribs):
        url = '{}?send_email=draft_registration'.format(url_project_contribs)
        payload = {
            'data': {
                'type': 'contributors',
                'attributes': {
                    'full_name': 'Kanye West',
                }
            }
        }

        with capture_signals() as mock_signal:
            res = app.post_json_api(url, payload, auth=user.auth)
        assert contributor_added in mock_signal.signals_sent()
        assert res.status_code == 201
        assert mock_mail.call_count == 0


class TestDraftContributorBulkCreate(DraftRegistrationCRUDTestCase, TestNodeContributorBulkCreate):
    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}draft_registrations/{}/contributors/?send_email=false'.format(
            API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}draft_registrations/{}/contributors/?send_email=false'.format(
            API_BASE, project_private._id)


class TestDraftContributorBulkUpdated(DraftRegistrationCRUDTestCase, TestNodeContributorBulkUpdate):

    @pytest.fixture()
    def project_public(
            self, user, user_two, user_three, title,
            description, category):
        project_public = DraftRegistrationFactory(
            initiator=user
        )
        project_public.add_contributor(
            user_two,
            permissions=permissions.READ,
            visible=True, save=True)
        project_public.add_contributor(
            user_three,
            permissions=permissions.READ,
            visible=True, save=True)
        return project_public

    @pytest.fixture()
    def project_private(
            self, user, user_two, user_three,
            title, description, category):
        project_private = DraftRegistrationFactory(
            initiator=user
        )
        project_private.add_contributor(
            user_two,
            permissions=permissions.READ,
            visible=True, save=True)
        project_private.add_contributor(
            user_three,
            permissions=permissions.READ,
            visible=True, save=True)
        return project_private

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}draft_registrations/{}/contributors/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}draft_registrations/{}/contributors/'.format(
            API_BASE, project_private._id)

class TestDraftRegistrationContributorBulkPartialUpdate(DraftRegistrationCRUDTestCase, TestNodeContributorBulkPartialUpdate):
    @pytest.fixture()
    def project_public(
            self, user, user_two, user_three, title,
            description, category):
        project_public = DraftRegistrationFactory(
            initiator=user
        )
        project_public.add_contributor(
            user_two,
            permissions=permissions.READ,
            visible=True, save=True)
        project_public.add_contributor(
            user_three,
            permissions=permissions.READ,
            visible=True, save=True)
        return project_public

    @pytest.fixture()
    def project_private(
            self, user, user_two, user_three,
            title, description, category):
        project_private = DraftRegistrationFactory(
            initiator=user
        )
        project_private.add_contributor(
            user_two,
            permissions=permissions.READ,
            visible=True, save=True)
        project_private.add_contributor(
            user_three,
            permissions=permissions.READ,
            visible=True, save=True)
        return project_private

    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}draft_registrations/{}/contributors/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}draft_registrations/{}/contributors/'.format(
            API_BASE, project_private._id)


class TestDraftRegistrationContributorBulkDelete(DraftRegistrationCRUDTestCase, TestNodeContributorBulkDelete):
    @pytest.fixture()
    def url_public(self, project_public):
        return '/{}draft_registrations/{}/contributors/'.format(API_BASE, project_public._id)

    @pytest.fixture()
    def url_private(self, project_private):
        return '/{}draft_registrations/{}/contributors/'.format(
            API_BASE, project_private._id)

    @pytest.fixture()
    def project_public(
            self, user, user_two, user_three, title,
            description, category):
        project_public = DraftRegistrationFactory(
            initiator=user
        )
        project_public.add_contributor(
            user_two,
            permissions=permissions.READ,
            visible=True, save=True)
        project_public.add_contributor(
            user_three,
            permissions=permissions.READ,
            visible=True, save=True)
        return project_public

    @pytest.fixture()
    def project_private(
            self, user, user_two, user_three,
            title, description, category):
        project_private = DraftRegistrationFactory(
            initiator=user
        )
        project_private.add_contributor(
            user_two,
            permissions=permissions.READ,
            visible=True, save=True)
        project_private.add_contributor(
            user_three,
            permissions=permissions.READ,
            visible=True, save=True)
        return project_private


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
@pytest.mark.enable_implicit_clean
class TestDraftRegistrationContributorFiltering(DraftRegistrationCRUDTestCase, TestNodeContributorFiltering):
    @pytest.fixture()
    def project(self, user):
        return DraftRegistrationFactory(initiator=user)

    @pytest.fixture()
    def url(self, project):
        return '/{}draft_registrations/{}/contributors/'.format(
            API_BASE, project._id)
