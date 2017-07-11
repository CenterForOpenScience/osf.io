# -*- coding: utf-8 -*-
import pytest
import mock

from addons.wiki.tests.factories import NodeWikiFactory
from api.base.settings import osf_settings
from api.base.settings.defaults import API_BASE
from api_tests import utils as test_utils
from framework.auth import core
from osf.models import Guid
from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    CommentFactory,
)
from rest_framework import exceptions


@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.mark.django_db
class NodeCommentsListMixin(object):

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_private_dict(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_public_dict(self):
        raise NotImplementedError

    @pytest.fixture()
    def registration_dict(self):
        raise NotImplementedError

    def test_return_comments(self, app, user, user_non_contrib, project_public_dict, project_private_dict, registration_dict):

    #   test_return_public_node_comments_logged_out_user
        res = app.get(project_public_dict['url'])
        assert res.status_code == 200
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert len(comment_json) == 1
        assert project_public_dict['comment']._id in comment_ids

    #   test_return_public_node_comments_logged_in_user
        res = app.get(project_public_dict['url'], auth=user_non_contrib)
        assert res.status_code == 200
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert len(comment_json) == 1
        assert project_public_dict['comment']._id in comment_ids

    #   test_return_private_node_comments_logged_out_user
        res = app.get(project_private_dict['url'], expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_return_private_node_comments_logged_in_non_contributor
        res = app.get(project_private_dict['url'], auth=user_non_contrib, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_return_private_node_comments_logged_in_contributor
        res = app.get(project_private_dict['url'], auth=user.auth)
        assert res.status_code == 200
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert len(comment_json) == 1
        assert project_private_dict['comment']._id in comment_ids

    #   test_return_registration_comments_logged_in_contributor
        res = app.get(registration_dict['url'], auth=user.auth)
        assert res.status_code == 200
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert len(comment_json) == 1
        assert registration_dict['comment']._id in comment_ids

    def test_return_both_deleted_and_undeleted_comments(self, app, user, project_private_dict, mock_update_search=None):
        deleted_comment = CommentFactory(node=project_private_dict['project'], user=user, target=project_private_dict['comment'].target, is_deleted=True)
        res = app.get(project_private_dict['url'], auth=user.auth)
        assert res.status_code == 200
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert project_private_dict['comment']._id in comment_ids
        assert deleted_comment._id in comment_ids

    def test_node_comments_pagination(self, app, user, project_public_dict):

    #   test_node_comments_list_pagination
        url = '{}?filter[target]={}&related_counts=False'.format(project_public_dict['url'], project_public_dict['project']._id)
        res = app.get(url, user=user, auth=user.auth)
        assert res.status_code == 200
        assert res.json['links']['meta']['unread'] == 0

    #   test_node_comments_list_updated_pagination
        url = '{}?filter[target]={}&related_counts=False&version=2.1'.format(project_public_dict['url'], project_public_dict['project']._id)
        res = app.get(url, user=user, auth=user.auth)
        assert res.status_code == 200
        assert res.json['meta']['unread'] == 0


@pytest.mark.django_db
class TestNodeCommentsList(NodeCommentsListMixin):

    @pytest.fixture()
    def project_private_dict(self, user):
        project_private = ProjectFactory(is_public=False, creator=user)
        comment_private = CommentFactory(node=project_private, user=user)
        url_private = '/{}nodes/{}/comments/'.format(API_BASE, project_private._id)
        return {'project': project_private, 'comment': comment_private, 'url': url_private}

    @pytest.fixture()
    def project_public_dict(self, user):
        project_public = ProjectFactory(is_public=True, creator=user)
        comment_public = CommentFactory(node=project_public, user=user)
        url_public = '/{}nodes/{}/comments/'.format(API_BASE, project_public._id)
        return {'project': project_public, 'comment': comment_public, 'url': url_public}

    @pytest.fixture()
    def registration_dict(self, user):
        registration = RegistrationFactory(creator=user)
        comment_registration = CommentFactory(node=registration, user=user)
        url_registration = '/{}registrations/{}/comments/'.format(API_BASE, registration._id)
        return {'registration': registration, 'comment': comment_registration, 'url': url_registration}


@pytest.mark.django_db
class TestNodeCommentsListFiles(NodeCommentsListMixin):

    @pytest.fixture()
    def project_private_dict(self, user):
        project_private = ProjectFactory(is_public=False, creator=user)
        file_private = test_utils.create_test_file(project_private, user)
        comment_private = CommentFactory(node=project_private, user=user, target=file_private.get_guid(), page='files')
        url_private = '/{}nodes/{}/comments/'.format(API_BASE, project_private._id)
        return {'project': project_private, 'file': file_private, 'comment': comment_private, 'url': url_private}

    @pytest.fixture()
    def project_public_dict(self, user):
        project_public = ProjectFactory(is_public=True, creator=user)
        file_public = test_utils.create_test_file(project_public, user)
        comment_public = CommentFactory(node=project_public, user=user, target=file_public.get_guid(), page='files')
        url_public = '/{}nodes/{}/comments/'.format(API_BASE, project_public._id)
        return {'project': project_public, 'file': file_public, 'comment': comment_public, 'url': url_public}

    @pytest.fixture()
    def registration_dict(self, user):
        registration = RegistrationFactory(creator=user)
        file_registration = test_utils.create_test_file(registration, user)
        comment_registration = CommentFactory(node=registration, user=user, target=file_registration.get_guid(), page='files')
        url_registration = '/{}registrations/{}/comments/'.format(API_BASE, registration._id)
        return {'registration': registration, 'file': file_registration, 'comment': comment_registration, 'url': url_registration}

    def test_comments_on_deleted_files_are_not_returned(self, app, user, project_private_dict):
        # Delete commented file
        osfstorage = project_private_dict['project'].get_addon('osfstorage')
        root_node = osfstorage.get_root()
        # root_node.delete(project_private_dict['file'])
        project_private_dict['file'].delete(user=user)
        res = app.get(project_private_dict['url'], auth=user.auth)
        assert res.status_code == 200
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert project_private_dict['comment']._id not in comment_ids


@pytest.mark.django_db
class TestNodeCommentsListWiki(NodeCommentsListMixin):

    @pytest.fixture()
    def project_private_dict(self, user):
        project_private = ProjectFactory(is_public=False, creator=user)
        wiki_private = NodeWikiFactory(node=project_private, user=user)
        comment_private = CommentFactory(node=project_private, user=user, target=Guid.load(wiki_private._id), page='wiki')
        url_private = '/{}nodes/{}/comments/'.format(API_BASE, project_private._id)
        return {'project': project_private, 'wiki': wiki_private, 'comment': comment_private, 'url': url_private}

    @pytest.fixture()
    def project_public_dict(self, user):
        project_public = ProjectFactory(is_public=True, creator=user)
        wiki_public = NodeWikiFactory(node=project_public, user=user)
        comment_public = CommentFactory(node=project_public, user=user, target=Guid.load(wiki_public._id), page='wiki')
        url_public = '/{}nodes/{}/comments/'.format(API_BASE, project_public._id)
        return {'project': project_public, 'wiki': wiki_public, 'comment': comment_public, 'url': url_public}

    @pytest.fixture()
    def registration_dict(self, user):
        registration = RegistrationFactory(creator=user)
        wiki_registration = NodeWikiFactory(node=registration, user=user)
        comment_registration = CommentFactory(node=registration, user=user, target=Guid.load(wiki_registration._id), page='wiki')
        url_registration = '/{}registrations/{}/comments/'.format(API_BASE, registration._id)
        return {'registration': registration, 'wiki': wiki_registration, 'comment': comment_registration, 'url': url_registration}

    def test_comments_on_deleted_wikis_are_not_returned(self, app, user, project_private_dict, mock_update_search=None):
        # Delete wiki
        project_private_dict['project'].delete_node_wiki(project_private_dict['wiki'].page_name, core.Auth(user))
        res = app.get(project_private_dict['url'], auth=user.auth)
        assert res.status_code == 200
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert project_private_dict['comment']._id not in comment_ids

@pytest.mark.django_db
class NodeCommentsCreateMixin(object):

    @pytest.fixture()
    def user_read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def payload(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_private_comment_private(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_public_comment_private(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_public_comment_public(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_private_comment_public(self):
        raise NotImplementedError

    def test_node_comments(self, app, user, user_read_contrib, user_non_contrib, project_private_comment_private, project_private_comment_public, project_public_comment_public, project_public_comment_private):

    #   test_private_node_private_comment_level_logged_in_admin_can_comment
        project_dict = project_private_comment_private
        res = app.post_json_api(project_dict['url'], project_dict['payload'], auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['content'] == project_dict['payload']['data']['attributes']['content']

    #   test_private_node_private_comment_level_logged_in_read_contributor_can_comment
        project_dict = project_private_comment_private
        res = app.post_json_api(project_dict['url'], project_dict['payload'], auth=user_read_contrib.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['content'] == project_dict['payload']['data']['attributes']['content']

    #   test_private_node_private_comment_level_non_contributor_cannot_comment
        project_dict = project_private_comment_private
        res = app.post_json_api(project_dict['url'], project_dict['payload'], auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_private_node_private_comment_level_logged_out_user_cannot_comment
        project_dict = project_private_comment_private
        res = app.post_json_api(project_dict['url'], project_dict['payload'], expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_private_node_with_public_comment_level_admin_can_comment
        # Test admin contributors can still comment on a private project with comment_level == 'public'
        project_dict = project_private_comment_public
        res = app.post_json_api(project_dict['url'], project_dict['payload'], auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['content'] == project_dict['payload']['data']['attributes']['content']

    #   test_private_node_with_public_comment_level_read_only_contributor_can_comment
        # Test read-only contributors can still comment on a private project with comment_level == 'public'
        project_dict = project_private_comment_public
        res = app.post_json_api(project_dict['url'], project_dict['payload'], auth=user_read_contrib.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['content'] == project_dict['payload']['data']['attributes']['content']

    #   test_private_node_with_public_comment_level_non_contributor_cannot_comment
        # Test non-contributors cannot comment on a private project with comment_level == 'public'
        project_dict = project_private_comment_public
        res = app.post_json_api(project_dict['url'], project_dict['payload'], auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

    #   test_private_node_with_public_comment_level_logged_out_user_cannot_comment
        # Test logged out users cannot comment on a private project with comment_level == 'public'
        project_dict = project_private_comment_public
        res = app.post_json_api(project_dict['url'], project_dict['payload'], expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_public_project_with_public_comment_level_admin_can_comment
        # Test admin contributor can still comment on a public project when it is configured so any logged-in user can comment (comment_level == 'public')
        project_dict = project_public_comment_public
        res = app.post_json_api(project_dict['url'], project_dict['payload'], auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['content'] == project_dict['payload']['data']['attributes']['content']

    #   test_public_project_with_public_comment_level_read_only_contributor_can_comment
        # Test read-only contributor can still comment on a public project when it is configured so any logged-in user can comment (comment_level == 'public')
        project_dict = project_public_comment_public
        res = app.post_json_api(project_dict['url'], project_dict['payload'], auth=user_read_contrib.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['content'] == project_dict['payload']['data']['attributes']['content']

    #   test_public_project_with_public_comment_level_non_contributor_can_comment
        # Test non-contributors can comment on a public project when it is configured so any logged-in user can comment (comment_level == 'public')
        project_dict = project_public_comment_public
        res = app.post_json_api(project_dict['url'], project_dict['payload'], auth=user_non_contrib.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['content'] == project_dict['payload']['data']['attributes']['content']

    #   test_public_project_with_public_comment_level_logged_out_user_cannot_comment
        # Test logged out users cannot comment on a public project when it is configured so any logged-in user can comment (comment_level == 'public')
        project_dict = project_public_comment_public
        res = app.post_json_api(project_dict['url'], project_dict['payload'], expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_public_node_private_comment_level_admin_can_comment
        # Test only contributors can comment on a public project when it is configured so only contributors can comment (comment_level == 'private')
        project_dict = project_public_comment_private
        res = app.post_json_api(project_dict['url'], project_dict['payload'], auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['content'] == project_dict['payload']['data']['attributes']['content']

    #   test_public_node_private_comment_level_read_only_contributor_can_comment
        project_dict = project_public_comment_private
        res = app.post_json_api(project_dict['url'], project_dict['payload'], auth=user_read_contrib.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['content'] == project_dict['payload']['data']['attributes']['content']

    #   test_public_node_private_comment_level_non_contributor_cannot_comment
        project_dict = project_public_comment_private
        res = app.post_json_api(project_dict['url'], project_dict['payload'], auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_public_node_private_comment_level_logged_out_user_cannot_comment
        project_dict = project_public_comment_private
        res = app.post_json_api(project_dict['url'], project_dict['payload'], expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail


@pytest.mark.django_db
class TestNodeCommentCreate(NodeCommentsCreateMixin):

    @pytest.fixture()
    def payload(self):
        def make_payload(target_id):
            return {
                'data': {
                    'type': 'comments',
                    'attributes': {
                        'content': 'This is a comment'
                    },
                    'relationships': {
                        'target': {
                            'data': {
                                'type': 'nodes',
                                'id': target_id
                            }
                        }
                    }
                }
            }
        return make_payload

    @pytest.fixture()
    def project_private_comment_private(self, user, user_read_contrib, payload):
        project_private = ProjectFactory(is_public=False, creator=user, comment_level='private')
        project_private.add_contributor(user_read_contrib, permissions=['read'])
        project_private.save()
        url_private = '/{}nodes/{}/comments/'.format(API_BASE, project_private._id)
        payload_private = payload(project_private._id)
        return {'project': project_private, 'url': url_private, 'payload': payload_private}

    @pytest.fixture()
    def project_public_comment_private(self, user, user_read_contrib, payload):
        project_public = ProjectFactory(is_public=True, creator=user, comment_level='private')
        project_public.add_contributor(user_read_contrib, permissions=['read'])
        project_public.save()
        url_public = '/{}nodes/{}/comments/'.format(API_BASE, project_public._id)
        payload_public = payload(project_public._id)
        return {'project': project_public, 'url': url_public, 'payload': payload_public}

    @pytest.fixture()
    def project_public_comment_public(self, user, user_read_contrib, payload):
        """ Public project configured so that any logged-in user can comment."""
        project_public = ProjectFactory(is_public=True, creator=user)
        project_public.add_contributor(user_read_contrib, permissions=['read'])
        project_public.save()
        url_public = '/{}nodes/{}/comments/'.format(API_BASE, project_public._id)
        payload_public = payload(project_public._id)
        return {'project': project_public, 'url': url_public, 'payload': payload_public}

    @pytest.fixture()
    def project_private_comment_public(self, user, user_read_contrib, payload):
        project_private = ProjectFactory(is_public=False, creator=user)
        project_private.add_contributor(user_read_contrib, permissions=['read'])
        project_private.save()
        url_private = '/{}nodes/{}/comments/'.format(API_BASE, project_private._id)
        payload_private = payload(project_private._id)
        return {'project': project_private, 'url': url_private, 'payload': payload_private}

    def test_create_comment_errors(self, app, user, payload, project_private_comment_private):

    #   test_create_comment_invalid_data
        project_dict = project_private_comment_private
        res = app.post_json_api(project_dict['url'], 'Incorrect data', auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    #   test_create_comment_no_relationships
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': '4:44'
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data/relationships.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/relationships'

    #   test_create_comment_empty_relationships
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'Center for Closed Logic'
                },
                'relationships': {}
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data/relationships.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/relationships'

    #   test_create_comment_relationship_is_a_list
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': [{'id': project_dict['project']._id}]
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    #   test_create_comment_target_no_data_in_relationships
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {}
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /data.'
        assert res.json['errors'][0]['source']['pointer'] == 'data/relationships/target/data'

    #   test_create_comment_no_target_key_in_relationships
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'data': {
                        'type': 'nodes',
                        'id': project_dict['project']._id
                    }
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == exceptions.ParseError.default_detail

    #   test_create_comment_blank_target_id
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': ''
                        }
                    }
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid comment target \'\'.'

    #   test_create_comment_invalid_target_id
        project_dict = project_private_comment_private
        project_id = ProjectFactory()._id
        payload_project = payload(project_id)
        res = app.post_json_api(project_dict['url'], payload_project, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid comment target \'' + str(project_id) + '\'.'

    #   test_create_comment_invalid_target_type
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'Invalid',
                            'id': project_dict['project']._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'The target resource has a type of "nodes", but you set the json body\'s type field to "Invalid".  You probably need to change the type field to match the target resource\'s type.'

    #   test_create_comment_no_target_type_in_relationships
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'id': project_dict['project']._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Request must include /type.'

    #   test_create_comment_no_type
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': '',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': project_dict['project']._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be blank.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

    #   test_create_comment_no_content
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': ''
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': project_dict['project']._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be blank.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/attributes/content'

    #   test_create_comment_trims_whitespace
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': '   '
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': project_dict['project']._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be blank.'

    #   test_create_comment_exceeds_max_length
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': ('c' * (osf_settings.COMMENT_MAXLENGTH + 3))
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': project_dict['project']._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Ensure this field has no more than {} characters.'.format(str(osf_settings.COMMENT_MAXLENGTH))

    #   test_create_comment_invalid_target_node
        url_fake = '/{}nodes/{}/comments/'.format(API_BASE, 'abcde')
        payload_fake = payload('abcde')
        res = app.post_json_api(url_fake, payload_fake, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
        assert res.json['errors'][0]['detail'] == exceptions.NotFound.default_detail

    def test_create_comment_with_allowed_tags(self, app, user, project_private_comment_private):
        project_dict = project_private_comment_private
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': '<em>Logic</em> <strong>Reason</strong>'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': project_dict['project']._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['attributes']['content'] == payload['data']['attributes']['content']


@pytest.mark.django_db
class TestFileCommentCreate(NodeCommentsCreateMixin):

    @pytest.fixture()
    def payload(self):
        def make_payload(target_id):
            return {
                'data': {
                    'type': 'comments',
                    'attributes': {
                        'content': 'This is a comment'
                    },
                    'relationships': {
                        'target': {
                            'data': {
                                'type': 'files',
                                'id': target_id
                            }
                        }
                    }
                }
            }
        return make_payload

    @pytest.fixture()
    def project_private_comment_private(self, user, user_read_contrib, payload):
        project_private = ProjectFactory(is_public=False, creator=user, comment_level='private')
        project_private.add_contributor(user_read_contrib, permissions=['read'])
        project_private.save()
        url_private = '/{}nodes/{}/comments/'.format(API_BASE, project_private._id)
        file_private = test_utils.create_test_file(project_private, user)
        payload_private = payload(file_private.get_guid()._id)
        return {'project': project_private, 'url': url_private, 'file': file_private, 'payload': payload_private}

    @pytest.fixture()
    def project_public_comment_private(self, user, user_read_contrib, payload):
        project_public = ProjectFactory(is_public=True, creator=user, comment_level='private')
        project_public.add_contributor(user_read_contrib, permissions=['read'])
        project_public.save()
        url_public = '/{}nodes/{}/comments/'.format(API_BASE, project_public._id)
        file_public = test_utils.create_test_file(project_public, user)
        payload_public = payload(file_public.get_guid()._id)
        return {'project': project_public, 'url': url_public, 'file': file_public, 'payload': payload_public}

    @pytest.fixture()
    def project_public_comment_public(self, user, user_read_contrib, payload):
        """ Public project configured so that any logged-in user can comment."""
        project_public = ProjectFactory(is_public=True, creator=user)
        project_public.add_contributor(user_read_contrib, permissions=['read'])
        project_public.save()
        url_public = '/{}nodes/{}/comments/'.format(API_BASE, project_public._id)
        file_public = test_utils.create_test_file(project_public, user)
        payload_public = payload(file_public.get_guid()._id)
        return {'project': project_public, 'url': url_public, 'file': file_public, 'payload': payload_public}

    @pytest.fixture()
    def project_private_comment_public(self, user, user_read_contrib, payload):
        project_private = ProjectFactory(is_public=False, creator=user)
        project_private.add_contributor(user_read_contrib, permissions=['read'])
        project_private.save()
        url_private = '/{}nodes/{}/comments/'.format(API_BASE, project_private._id)
        file_private = test_utils.create_test_file(project_private, user)
        payload_private = payload(file_private.get_guid()._id)
        return {'project': project_private, 'url': url_private, 'file': file_private, 'payload': payload_private}

    def test_create_file_comment_errors(self, app, user, payload, project_private_comment_private):

    #   test_create_file_comment_invalid_target_id
        project_dict = project_private_comment_private
        file = test_utils.create_test_file(ProjectFactory(), user)
        payload_req = payload(file._id)
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid comment target \'' + str(file._id) + '\'.'

    #   test_create_file_comment_invalid_target_type
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'Invalid',
                            'id': project_dict['file'].get_guid()._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'The target resource has a type of "files", but you set the json body\'s type field to "Invalid".  You probably need to change the type field to match the target resource\'s type.'


@pytest.mark.django_db
class TestWikiCommentCreate(NodeCommentsCreateMixin):

    @pytest.fixture()
    def payload(self):
        def make_payload(target_id):
            return {
                'data': {
                    'type': 'comments',
                    'attributes': {
                        'content': 'This is a comment'
                    },
                    'relationships': {
                        'target': {
                            'data': {
                                'type': 'wiki',
                                'id': target_id
                            }
                        }
                    }
                }
            }
        return make_payload

    @pytest.fixture()
    def project_private_comment_private(self, user, user_read_contrib, payload):
        project_private = ProjectFactory(is_public=False, creator=user, comment_level='private')
        project_private.add_contributor(user_read_contrib, permissions=['read'])
        project_private.save()
        url_private = '/{}nodes/{}/comments/'.format(API_BASE, project_private._id)
        wiki = NodeWikiFactory(node=project_private, user=user)
        payload_private = payload(wiki._id)
        return {'project': project_private, 'url': url_private, 'wiki': wiki, 'payload': payload_private}

    @pytest.fixture()
    def project_public_comment_private(self, user, user_read_contrib, payload):
        project_public = ProjectFactory(is_public=True, creator=user, comment_level='private')
        project_public.add_contributor(user_read_contrib, permissions=['read'])
        project_public.save()
        url_public = '/{}nodes/{}/comments/'.format(API_BASE, project_public._id)
        wiki = NodeWikiFactory(node=project_public, user=user)
        payload_public = payload(wiki._id)
        return {'project': project_public, 'url': url_public, 'wiki': wiki, 'payload': payload_public}

    @pytest.fixture()
    def project_public_comment_public(self, user, user_read_contrib, payload):
        """ Public project configured so that any logged-in user can comment."""
        project_public = ProjectFactory(is_public=True, creator=user)
        project_public.add_contributor(user_read_contrib, permissions=['read'])
        project_public.save()
        url_public = '/{}nodes/{}/comments/'.format(API_BASE, project_public._id)
        wiki = NodeWikiFactory(node=project_public, user=user)
        payload_public = payload(wiki._id)
        return {'project': project_public, 'url': url_public, 'wiki': wiki, 'payload': payload_public}

    @pytest.fixture()
    def project_private_comment_public(self, user, user_read_contrib, payload):
        project_private = ProjectFactory(is_public=False, creator=user)
        project_private.add_contributor(user_read_contrib, permissions=['read'])
        project_private.save()
        url_private = '/{}nodes/{}/comments/'.format(API_BASE, project_private._id)
        wiki = NodeWikiFactory(node=project_private, user=user)
        payload_private = payload(wiki._id)
        return {'project': project_private, 'url': url_private, 'wiki': wiki, 'payload': payload_private}

    def test_create_wiki_comment_errors(self, app, user, payload, project_private_comment_private, mock_update_search=None):

    #   test_create_wiki_comment_invalid_target_id
        project_dict = project_private_comment_private
        wiki = NodeWikiFactory(node=ProjectFactory(), user=user)
        payload_req = payload(wiki._id)
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid comment target \'' + str(wiki._id) + '\'.'

    #   test_create_wiki_comment_invalid_target_type
        project_dict = project_private_comment_private
        payload_req = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'Invalid',
                            'id': project_dict['wiki']._id
                        }
                    }
                }
            }
        }
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'The target resource has a type of "wiki", but you set the json body\'s type field to "Invalid".  You probably need to change the type field to match the target resource\'s type.'


@pytest.mark.django_db
class TestCommentRepliesCreate(NodeCommentsCreateMixin):

    @pytest.fixture()
    def payload(self):
        def make_payload(comment_id):
            return {
                'data': {
                    'type': 'comments',
                    'attributes': {
                        'content': 'This is a comment'
                    },
                    'relationships': {
                        'target': {
                            'data': {
                                'type': 'comments',
                                'id': comment_id
                            }
                        }
                    }
                }
            }
        return make_payload

    @pytest.fixture()
    def project_private_comment_private(self, user, user_read_contrib, payload):
        project_private = ProjectFactory.create(is_public=False, creator=user, comment_level='private')
        project_private.add_contributor(user_read_contrib, permissions=['read'], save=True)
        comment_private = CommentFactory(node=project_private, user=user)
        url_private = '/{}nodes/{}/comments/'.format(API_BASE, project_private._id)
        payload_private = payload(comment_private._id)
        return {'project': project_private, 'comment': comment_private, 'url': url_private, 'payload': payload_private}

    @pytest.fixture()
    def project_public_comment_private(self, user, user_read_contrib, payload):
        project_public = ProjectFactory.create(is_public=True, creator=user, comment_level='private')
        project_public.add_contributor(user_read_contrib, permissions=['read'], save=True)
        comment_public = CommentFactory(node=project_public, user=user)
        url_public = '/{}nodes/{}/comments/'.format(API_BASE, project_public._id)
        payload_public = payload(comment_public._id)
        return {'project': project_public, 'comment': comment_public, 'url': url_public, 'payload': payload_public}

    @pytest.fixture()
    def project_private_comment_public(self, user, user_read_contrib, payload):
        project_private = ProjectFactory(is_public=False, creator=user)
        project_private.add_contributor(user_read_contrib, permissions=['read'], save=True)
        comment_private = CommentFactory(node=project_private, user=user)
        comment_reply = CommentFactory(node=project_private, target=Guid.load(comment_private._id), user=user)
        url_private = '/{}nodes/{}/comments/'.format(API_BASE, project_private._id)
        payload_private = payload(comment_reply._id)
        return {'project': project_private, 'comment': comment_private, 'reply': comment_reply, 'url': url_private, 'payload': payload_private}

    @pytest.fixture()
    def project_public_comment_public(self, user, user_read_contrib, payload):
        project_public = ProjectFactory(is_public=True, creator=user)
        project_public.add_contributor(user_read_contrib, permissions=['read'], save=True)
        comment_public = CommentFactory(node=project_public, user=user)
        comment_reply = CommentFactory(node=project_public, target=Guid.load(comment_public._id), user=user)
        url_public = '/{}nodes/{}/comments/'.format(API_BASE, project_public._id)
        payload_public = payload(comment_reply._id)
        return {'project': project_public, 'comment': comment_public, 'reply': comment_reply, 'url': url_public, 'payload': payload_public}

    def test_create_comment_reply_invalid_target_id(self, app, user, payload, project_private_comment_private):
        project_dict = project_private_comment_private
        target_comment = CommentFactory(node=ProjectFactory(), user=user)
        payload_req = payload(target_comment._id)
        res = app.post_json_api(project_dict['url'], payload_req, auth=user.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Invalid comment target \'' + str(target_comment._id) + '\'.'


@pytest.mark.django_db
class TestCommentFiltering:

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def comment(self, user, project):
        return CommentFactory(node=project, user=user, page='node')

    @pytest.fixture()
    def comment_deleted(self, user, project):
        return CommentFactory(node=project, user=user, is_deleted=True, page='node')

    @pytest.fixture()
    def url_base(self, project):
        return '/{}nodes/{}/comments/'.format(API_BASE, project._id)

    @pytest.fixture()
    def date_created_formatted(self, comment):
        return comment.date_created.strftime('%Y-%m-%dT%H:%M:%S.%f')

    @pytest.fixture()
    def date_modified_formatted(self, user, comment):
        comment.edit('Edited comment', auth=core.Auth(user), save=True)
        return comment.date_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')

    def test_filtering(self, app, user, project, comment, comment_deleted, date_created_formatted, date_modified_formatted, url_base):

    #   test_node_comments_with_no_filter_returns_all_comments
        res = app.get(url_base, auth=user.auth)
        assert len(res.json['data']) == 2

    #   test_filtering_for_deleted_comments
        assert comment
        assert comment_deleted
        url = url_base + '?filter[deleted]=True'
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['attributes']['deleted']

    #   test_filtering_for_non_deleted_comments
        assert comment
        assert comment_deleted
        url = url_base + '?filter[deleted]=False'
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1
        assert not res.json['data'][0]['attributes']['deleted']

    #   test_filtering_comments_created_before_date
        url = url_base + '?filter[date_created][lt]={}'.format(date_created_formatted)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 0

    #   test_filtering_comments_created_on_date
        url = url_base + '?filter[date_created][eq]={}'.format(date_created_formatted)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1

    #   test_filtering_comments_created_on_or_before_date
        url = url_base + '?filter[date_created][lte]={}'.format(date_created_formatted)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1

    #   test_filtering_comments_created_after_date
        url = url_base + '?filter[date_created][gt]={}'.format(date_created_formatted)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1

    #   test_filtering_comments_created_on_or_after_date
        url = url_base + '?filter[date_created][gte]={}'.format(date_created_formatted)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 2

    #   test_filtering_comments_modified_before_date
        url = url_base + '?filter[date_modified][lt]={}'.format(date_modified_formatted)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1

    #   test_filtering_comments_modified_on_date
        url = url_base + '?filter[date_modified][eq]={}'.format(date_modified_formatted)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1

    #   test_filtering_comments_modified_after_date
        url = url_base + '?filter[date_modified][gt]={}'.format(date_modified_formatted)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 0

    #   test_filtering_by_target_node
        url = url_base + '?filter[target]=' + str(project._id)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 2
        assert project._id in res.json['data'][0]['relationships']['target']['links']['related']['href']
        assert project._id in res.json['data'][1]['relationships']['target']['links']['related']['href']

    #   test_filtering_by_target_no_results
        url = url_base + '?filter[target]=' + 'fakeid'
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 0

    #   test_filtering_by_target_no_results_with_related_counts
        url = '{}?filter[target]=fakeid&related_counts=True'.format(url_base)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 0

    #   test_filtering_by_page_node
        url = url_base + '?filter[page]=node'
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 2
        assert 'node' == res.json['data'][0]['attributes']['page']
        assert 'node' == res.json['data'][1]['attributes']['page']

    def test_filtering_for_comment_replies(self, app, user, project, comment, comment_deleted, url_base):
        reply = CommentFactory(node=project, user=user, target=Guid.load(comment._id))
        url = url_base + '?filter[target]=' + str(comment._id)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1
        assert comment._id in res.json['data'][0]['relationships']['target']['links']['related']['href']

    def test_filtering_by_target_file(self, app, user, project, comment, comment_deleted, url_base):
        test_file = test_utils.create_test_file(project, user)
        target = test_file.get_guid()
        file_comment = CommentFactory(node=project, user=user, target=target)
        url = url_base + '?filter[target]=' + str(target._id)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1
        assert test_file._id in res.json['data'][0]['relationships']['target']['links']['related']['href']

    def test_filtering_by_target_wiki(self, app, user, project, comment, comment_deleted, url_base):
        test_wiki = NodeWikiFactory(node=project, user=user)
        wiki_comment = CommentFactory(node=project, user=user, target=Guid.load(test_wiki._id), page='wiki')
        url = url_base + '?filter[target]=' + str(test_wiki._id)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1
        assert test_wiki.get_absolute_url() == res.json['data'][0]['relationships']['target']['links']['related']['href']

    def test_filtering_by_page_files(self, app, user, project, comment, comment_deleted, url_base):
        test_file = test_utils.create_test_file(project, user)
        file_comment = CommentFactory(node=project, user=user, target=test_file.get_guid(), page='files')
        url = url_base + '?filter[page]=files'
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1
        assert 'files' == res.json['data'][0]['attributes']['page']

    def test_filtering_by_page_wiki(self, app, user, project, comment, comment_deleted, url_base):
        test_wiki = NodeWikiFactory(node=project, user=user)
        wiki_comment = CommentFactory(node=project, user=user, target=Guid.load(test_wiki._id), page='wiki')
        url = url_base + '?filter[page]=wiki'
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1
        assert 'wiki' == res.json['data'][0]['attributes']['page']
