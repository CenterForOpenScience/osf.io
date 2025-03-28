from unittest import mock
import pytest
from urllib.parse import urlparse

from rest_framework import exceptions
from api.base.settings.defaults import API_BASE
from api.taxonomies.serializers import subjects_as_relationships_version
from api_tests.subjects.mixins import UpdateSubjectsMixin
from osf.utils import permissions
from osf.models import NodeLog
from framework.auth import Auth
from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory
from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    WithdrawnRegistrationFactory,
    CommentFactory,
)

from api_tests.nodes.views.test_node_detail import TestNodeUpdateLicense
from tests.utils import assert_latest_log
from api_tests.utils import create_test_file


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestRegistrationDetail:

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(
            title='Public Project',
            is_public=True,
            creator=user)

    @pytest.fixture()
    def private_project(self, user):
        private_project = ProjectFactory(title='Private Project', creator=user)
        create_test_file(private_project, user, filename='sake recipe')
        create_test_file(private_project, user, filename='sake rice wine recipe')
        deleted_file = create_test_file(private_project, user, filename='No sake')
        deleted_file.delete()
        return private_project

    @pytest.fixture()
    def public_registration(self, user, public_project):
        return RegistrationFactory(
            project=public_project,
            creator=user,
            is_public=True,
            comment_level='private')

    @pytest.fixture()
    def private_wiki(self, user, private_project):
        with mock.patch('osf.models.AbstractNode.update_search'):
            wiki_page = WikiFactory(node=private_project, user=user)
            WikiVersionFactory(wiki_page=wiki_page)
        return wiki_page

    @pytest.fixture()
    def private_registration(self, user, private_project, private_wiki):
        return RegistrationFactory(project=private_project, creator=user)

    @pytest.fixture()
    def registration_comment(self, private_registration, user):
        return CommentFactory(
            node=private_registration,
            user=user,
            page='node',
        )

    @pytest.fixture()
    def registration_comment_reply(self, user, private_registration, registration_comment):
        return CommentFactory(
            node=private_registration,
            target=registration_comment.guids.first(),
            user=user,
            page='node',
        )

    @pytest.fixture()
    def registration_wiki_comment(self, user, private_registration):
        return CommentFactory(
            node=private_registration,
            target=private_registration.wikis.first().guids.first(),
            user=user,
            page='wiki',
        )

    @pytest.fixture()
    def public_url(self, public_registration):
        return f'/{API_BASE}registrations/{public_registration._id}/'

    @pytest.fixture()
    def private_url(self, private_registration):
        return '/{}registrations/{}/'.format(
            API_BASE, private_registration._id)

    def test_registration_detail(
            self, app, user, public_project, private_project,
            public_registration, private_registration, private_wiki,
            public_url, private_url, registration_comment, registration_comment_reply,
            registration_wiki_comment):

        non_contributor = AuthUserFactory()

    #   test_return_public_registration_details_logged_out
        res = app.get(public_url)
        assert res.status_code == 200
        data = res.json['data']
        registered_from = urlparse(
            data['relationships']['registered_from']['links']['related']['href']
        ).path
        assert data['attributes']['registration'] is True
        assert data['attributes']['current_user_is_contributor'] is False
        assert registered_from == '/{}nodes/{}/'.format(
            API_BASE, public_project._id)

    #   test_return_public_registration_details_logged_in
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        data = res.json['data']
        registered_from = urlparse(
            data['relationships']['registered_from']['links']['related']['href']).path
        assert data['attributes']['registration'] is True
        assert data['attributes']['current_user_is_contributor'] is True
        assert registered_from == '/{}nodes/{}/'.format(
            API_BASE, public_project._id)

    #   test_return_private_registration_details_logged_out
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401
        assert 'detail' in res.json['errors'][0]

    #   test_return_private_project_registrations_logged_in_contributor
        res = app.get(private_url, auth=user.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        data = res.json['data']
        registered_from = urlparse(
            data['relationships']['registered_from']['links']['related']['href']).path
        assert data['attributes']['registration'] is True
        assert data['attributes']['has_project'] is True
        assert data['attributes']['current_user_is_contributor'] is True
        assert registered_from == '/{}nodes/{}/'.format(
            API_BASE, private_project._id)

    #   test_return_private_registration_details_logged_in_non_contributor
        res = app.get(
            private_url,
            auth=non_contributor.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert 'detail' in res.json['errors'][0]

    #   test_do_not_return_node_detail
        url = f'/{API_BASE}registrations/{public_project._id}/'
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == exceptions.NotFound.default_detail

    #   test_do_not_return_node_detail_in_sub_view
        url = '/{}registrations/{}/contributors/'.format(
            API_BASE, public_project._id)
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == exceptions.NotFound.default_detail

    #   test_do_not_return_registration_in_node_detail
        url = f'/{API_BASE}nodes/{public_registration._id}/'
        res = app.get(url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == exceptions.NotFound.default_detail

    #   test_registration_shows_related_counts
        url = '/{}registrations/{}/?related_counts=True'.format(
            API_BASE, private_registration._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 0
        assert res.json['data']['relationships']['contributors']['links']['related']['meta']['count'] == 1
        assert res.json['data']['relationships']['comments']['links']['related']['meta']['count'] == 2
        assert res.json['data']['relationships']['wikis']['links']['related']['meta']['count'] == 1
        assert res.json['data']['relationships']['files']['links']['related']['meta']['count'] == 2

        registration_comment_reply.is_deleted = True
        registration_comment_reply.save()
        res = app.get(url, auth=user.auth)
        assert res.json['data']['relationships']['comments']['links']['related']['meta']['count'] == 1

    #   test_registration_shows_specific_related_counts
        url = '/{}registrations/{}/?related_counts=children,wikis'.format(
            API_BASE, private_registration._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['relationships']['children']['links']['related']['meta']['count'] == 0
        assert res.json['data']['relationships']['contributors']['links']['related']['meta'] == {}
        assert res.json['data']['relationships']['wikis']['links']['related']['meta']['count'] == 1

    #   test_hide_if_registration
        # Registrations are a HideIfRegistration field
        node_url = f'/{API_BASE}nodes/{private_project._id}/'
        res = app.get(node_url, auth=user.auth)
        assert res.status_code == 200
        assert 'registrations' in res.json['data']['relationships']

        res = app.get(private_url, auth=user.auth)
        assert res.status_code == 200
        assert 'registrations' not in res.json['data']['relationships']

    #   test_registration_has_subjects_links_for_later_versions
        res = app.get(public_url + f'?version={subjects_as_relationships_version}')
        related_url = res.json['data']['relationships']['subjects']['links']['related']['href']
        expected_url = f'{public_url}subjects/'
        assert urlparse(related_url).path == expected_url
        self_url = res.json['data']['relationships']['subjects']['links']['self']['href']
        expected_url = f'{public_url}relationships/subjects/'
        assert urlparse(self_url).path == expected_url


@pytest.mark.django_db
class TestRegistrationTags:

    @pytest.fixture()
    def user_admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def read_write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public(self, user_admin, read_write_contrib):
        project_public = ProjectFactory(
            title='Project One',
            is_public=True,
            creator=user_admin)
        project_public.add_contributor(
            user_admin,
            permissions=permissions.CREATOR_PERMISSIONS,
            save=True)
        project_public.add_contributor(
            read_write_contrib,
            permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS,
            save=True)
        return project_public

    @pytest.fixture()
    def registration_public(self, project_public, user_admin):
        return RegistrationFactory(
            project=project_public,
            creator=user_admin,
            is_public=True)

    @pytest.fixture()
    def registration_private(self, project_public, user_admin):
        return RegistrationFactory(
            project=project_public,
            creator=user_admin,
            is_public=False)

    @pytest.fixture()
    def registration_withdrawn(self, project_public, user_admin):
        return RegistrationFactory(
            project=project_public,
            creator=user_admin,
            is_public=True)

    @pytest.fixture()
    def withdrawn_registration(self, registration_withdrawn, user_admin):
        registration_withdrawn.add_tag(
            'existing-tag', auth=Auth(user=user_admin))
        registration_withdrawn.save()
        withdrawn_registration = WithdrawnRegistrationFactory(
            registration=registration_withdrawn, user=user_admin)
        withdrawn_registration.justification = 'We made a major error.'
        withdrawn_registration.save()
        return withdrawn_registration

    @pytest.fixture()
    def url_registration_public(self, registration_public):
        return '/{}registrations/{}/'.format(
            API_BASE, registration_public._id)

    @pytest.fixture()
    def url_registration_private(self, registration_private):
        return '/{}registrations/{}/'.format(
            API_BASE, registration_private._id)

    @pytest.fixture()
    def url_registration_withdrawn(
            self, registration_withdrawn, withdrawn_registration):
        return '/{}registrations/{}/'.format(
            API_BASE, registration_withdrawn._id)

    @pytest.fixture()
    def new_tag_payload_public(self, registration_public):
        return {
            'data': {
                'id': registration_public._id,
                'type': 'registrations',
                'attributes': {
                    'tags': ['new-tag'],
                }
            }
        }

    @pytest.fixture()
    def new_tag_payload_private(self, registration_private):
        return {
            'data': {
                'id': registration_private._id,
                'type': 'registrations',
                'attributes': {
                    'tags': ['new-tag'],
                }
            }
        }

    @pytest.fixture()
    def new_tag_payload_withdrawn(self, registration_withdrawn):
        return {
            'data': {
                'id': registration_withdrawn._id,
                'type': 'registrations',
                'attributes': {
                    'tags': ['new-tag', 'existing-tag'],
                }
            }
        }

    def test_registration_tags(
            self, app, registration_public, registration_private,
            url_registration_public, url_registration_private,
            new_tag_payload_public, new_tag_payload_private,
            user_admin, user_non_contrib, read_write_contrib):
        # test_registration_starts_with_no_tags
        res = app.get(url_registration_public)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 0

        # test_registration_does_not_expose_system_tags
        registration_public.add_system_tag('systag', save=True)
        res = app.get(url_registration_public)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 0

        # test_contributor_can_add_tag_to_public_registration
        with assert_latest_log(NodeLog.TAG_ADDED, registration_public):
            res = app.patch_json_api(
                url_registration_public,
                new_tag_payload_public,
                auth=user_admin.auth)
            assert res.status_code == 200
            # Ensure data is correct from the PATCH response
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'new-tag'
            # Ensure data is correct in the database
            registration_public.reload()
            assert registration_public.tags.count() == 1
            assert registration_public.tags.first()._id == 'new-tag'
            # Ensure data is correct when GETting the resource again
            reload_res = app.get(url_registration_public)
            assert len(reload_res.json['data']['attributes']['tags']) == 1
            assert reload_res.json['data']['attributes']['tags'][0] == 'new-tag'

        # test_contributor_can_add_tag_to_private_registration
        with assert_latest_log(NodeLog.TAG_ADDED, registration_private):
            res = app.patch_json_api(
                url_registration_private,
                new_tag_payload_private,
                auth=user_admin.auth)
            assert res.status_code == 200
            # Ensure data is correct from the PATCH response
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'new-tag'
            # Ensure data is correct in the database
            registration_private.reload()
            assert registration_private.tags.count() == 1
            assert registration_private.tags.first()._id == 'new-tag'
            # Ensure data is correct when GETting the resource again
            reload_res = app.get(
                url_registration_private,
                auth=user_admin.auth)
            assert len(reload_res.json['data']['attributes']['tags']) == 1
            assert reload_res.json['data']['attributes']['tags'][0] == 'new-tag'

        # test_non_contributor_cannot_add_tag_to_registration
        res = app.patch_json_api(
            url_registration_public,
            new_tag_payload_public,
            expect_errors=True,
            auth=user_non_contrib.auth)
        assert res.status_code == 403

        # test_partial_update_registration_does_not_clear_tags
        new_payload = {
            'data': {
                'id': registration_private._id,
                'type': 'registrations',
                'attributes': {
                    'public': True
                }
            }
        }
        res = app.patch_json_api(
            url_registration_private,
            new_payload,
            auth=user_admin.auth)
        assert res.status_code == 200
        assert len(res.json['data']['attributes']['tags']) == 1

        # test read-write contributor can update tags
        new_tag_payload_public['data']['attributes']['tags'] = ['from-readwrite']
        res = app.patch_json_api(
            url_registration_public,
            new_tag_payload_public,
            auth=read_write_contrib.auth)
        assert res.status_code == 200

    def test_tags_add_and_remove_properly(
            self, app, user_admin, registration_public,
            new_tag_payload_public, url_registration_public):
        with assert_latest_log(NodeLog.TAG_ADDED, registration_public):
            res = app.patch_json_api(
                url_registration_public,
                new_tag_payload_public,
                auth=user_admin.auth)
            assert res.status_code == 200
            # Ensure adding tag data is correct from the PATCH response
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'new-tag'
        with assert_latest_log(NodeLog.TAG_REMOVED, registration_public), assert_latest_log(NodeLog.TAG_ADDED, registration_public, 1):
            # Ensure removing and adding tag data is correct from the PATCH
            # response
            res = app.patch_json_api(
                url_registration_public,
                {
                    'data': {
                        'id': registration_public._id,
                        'type': 'registrations',
                        'attributes': {'tags': ['newer-tag']}
                    }
                }, auth=user_admin.auth)
            assert res.status_code == 200
            assert len(res.json['data']['attributes']['tags']) == 1
            assert res.json['data']['attributes']['tags'][0] == 'newer-tag'
        with assert_latest_log(NodeLog.TAG_REMOVED, registration_public):
            # Ensure removing tag data is correct from the PATCH response
            res = app.patch_json_api(
                url_registration_public,
                {
                    'data': {
                        'id': registration_public._id,
                        'type': 'registrations',
                        'attributes': {'tags': []}
                    }
                }, auth=user_admin.auth)
            assert res.status_code == 200
            assert len(res.json['data']['attributes']['tags']) == 0

    def test_tags_for_withdrawn_registration(
            self, app, registration_withdrawn, user_admin,
            url_registration_withdrawn, new_tag_payload_withdrawn):
        res = app.patch_json_api(
            url_registration_withdrawn,
            new_tag_payload_withdrawn,
            auth=user_admin.auth,
            expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'Cannot add tags to withdrawn registrations.'

        res = app.patch_json_api(
            url_registration_withdrawn,
            {
                'data': {
                    'id': registration_withdrawn._id,
                    'type': 'registrations',
                    'attributes': {'tags': []}
                }
            },
            auth=user_admin.auth,
            expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'Cannot remove tags of withdrawn registrations.'


class TestUpdateRegistrationLicense(TestNodeUpdateLicense):
    @pytest.fixture()
    def node(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        node = RegistrationFactory(creator=user_admin_contrib, is_public=False)
        node.add_contributor(user_write_contrib, auth=Auth(user_admin_contrib))
        node.add_contributor(
            user_read_contrib,
            auth=Auth(user_admin_contrib),
            permissions=permissions.READ)
        node.save()
        return node

    @pytest.fixture()
    def url_node(self, node):
        return f'/{API_BASE}registrations/{node._id}/'

    @pytest.fixture()
    def make_payload(self):
        def payload(
                node_id, license_id=None, license_year=None,
                copyright_holders=None):
            attributes = {}

            if license_year and copyright_holders:
                attributes = {
                    'node_license': {
                        'year': license_year,
                        'copyright_holders': copyright_holders
                    }
                }
            elif license_year:
                attributes = {
                    'node_license': {
                        'year': license_year
                    }
                }
            elif copyright_holders:
                attributes = {
                    'node_license': {
                        'copyright_holders': copyright_holders
                    }
                }

            return {
                'data': {
                    'type': 'registrations',
                    'id': node_id,
                    'attributes': attributes,
                    'relationships': {
                        'license': {
                            'data': {
                                'type': 'licenses',
                                'id': license_id
                            }
                        }
                    }
                }
            } if license_id else {
                'data': {
                    'type': 'registrations',
                    'id': node_id,
                    'attributes': attributes
                }
            }
        return payload


@pytest.mark.django_db
class TestUpdateRegistrationSubjects(UpdateSubjectsMixin):
    @pytest.fixture()
    def resource(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        registration = RegistrationFactory(creator=user_admin_contrib, is_public=False)
        registration.add_contributor(user_write_contrib, auth=Auth(user_admin_contrib))
        registration.add_contributor(
            user_read_contrib,
            auth=Auth(user_admin_contrib),
            permissions=permissions.READ)
        registration.save()
        return registration
