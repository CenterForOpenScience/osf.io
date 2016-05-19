# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from framework.auth import core
from framework.guid.model import Guid

from api.base.settings.defaults import API_BASE
from api.base.settings import osf_settings
from api_tests import utils as test_utils
from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    CommentFactory,
    NodeWikiFactory
)


class NodeCommentsListMixin(object):

    def setUp(self):
        super(NodeCommentsListMixin, self).setUp()
        self.user = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

    def _set_up_private_project_with_comment(self):
        raise NotImplementedError

    def _set_up_public_project_with_comment(self):
        raise NotImplementedError

    def _set_up_registration_with_comment(self):
        raise NotImplementedError

    def test_return_public_node_comments_logged_out_user(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.public_comment._id, comment_ids)

    def test_return_public_node_comments_logged_in_user(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url, auth=self.non_contributor)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.public_comment._id, comment_ids)

    def test_return_private_node_comments_logged_out_user(self):
        self._set_up_private_project_with_comment()
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_return_private_node_comments_logged_in_non_contributor(self):
        self._set_up_private_project_with_comment()
        res = self.app.get(self.private_url, auth=self.non_contributor, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_return_private_node_comments_logged_in_contributor(self):
        self._set_up_private_project_with_comment()
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.comment._id, comment_ids)

    def test_return_registration_comments_logged_in_contributor(self):
        self._set_up_registration_with_comment()
        res = self.app.get(self.registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.registration_comment._id, comment_ids)

    def test_return_both_deleted_and_undeleted_comments(self):
        self._set_up_private_project_with_comment()
        deleted_comment = CommentFactory(node=self.private_project, user=self.user, target=self.comment.target, is_deleted=True)
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_in(self.comment._id, comment_ids)
        assert_in(deleted_comment._id, comment_ids)


class TestNodeCommentsList(NodeCommentsListMixin, ApiTestCase):

    def _set_up_private_project_with_comment(self):
        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.comment = CommentFactory(node=self.private_project, user=self.user)
        self.private_url = '/{}nodes/{}/comments/'.format(API_BASE, self.private_project._id)

    def _set_up_public_project_with_comment(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_comment = CommentFactory(node=self.public_project, user=self.user)
        self.public_url = '/{}nodes/{}/comments/'.format(API_BASE, self.public_project._id)

    def _set_up_registration_with_comment(self):
        self.registration = RegistrationFactory(creator=self.user)
        self.registration_comment = CommentFactory(node=self.registration, user=self.user)
        self.registration_url = '/{}registrations/{}/comments/'.format(API_BASE, self.registration._id)


class TestNodeCommentsListFiles(NodeCommentsListMixin, ApiTestCase):

    def _set_up_private_project_with_comment(self):
        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.file = test_utils.create_test_file(self.private_project, self.user)
        self.comment = CommentFactory(node=self.private_project, user=self.user, target=self.file.get_guid(), page='files')
        self.private_url = '/{}nodes/{}/comments/'.format(API_BASE, self.private_project._id)

    def _set_up_public_project_with_comment(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_file = test_utils.create_test_file(self.public_project, self.user)
        self.public_comment = CommentFactory(node=self.public_project, user=self.user, target=self.public_file.get_guid(), page='files')
        self.public_url = '/{}nodes/{}/comments/'.format(API_BASE, self.public_project._id)

    def _set_up_registration_with_comment(self):
        self.registration = RegistrationFactory(creator=self.user)
        self.registration_file = test_utils.create_test_file(self.registration, self.user)
        self.registration_comment = CommentFactory(node=self.registration, user=self.user, target=self.registration_file.get_guid(), page='files')
        self.registration_url = '/{}registrations/{}/comments/'.format(API_BASE, self.registration._id)

    def test_comments_on_deleted_files_are_not_returned(self):
        self._set_up_private_project_with_comment()
        # Delete commented file
        osfstorage = self.private_project.get_addon('osfstorage')
        root_node = osfstorage.get_root()
        root_node.delete(self.file)

        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_not_in(self.comment._id, comment_ids)


class TestNodeCommentsListWiki(NodeCommentsListMixin, ApiTestCase):

    def _set_up_private_project_with_comment(self):
        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.wiki = NodeWikiFactory(node=self.private_project, user=self.user)
        self.comment = CommentFactory(node=self.private_project, user=self.user, target=Guid.load(self.wiki._id), page='wiki')
        self.private_url = '/{}nodes/{}/comments/'.format(API_BASE, self.private_project._id)

    def _set_up_public_project_with_comment(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_wiki = NodeWikiFactory(node=self.public_project, user=self.user)
        self.public_comment = CommentFactory(node=self.public_project, user=self.user, target=Guid.load(self.public_wiki._id), page='wiki')
        self.public_url = '/{}nodes/{}/comments/'.format(API_BASE, self.public_project._id)

    def _set_up_registration_with_comment(self):
        self.registration = RegistrationFactory(creator=self.user)
        self.registration_wiki = NodeWikiFactory(node=self.registration, user=self.user)
        self.registration_comment = CommentFactory(node=self.registration, user=self.user, target=Guid.load(self.registration_wiki._id), page='wiki')
        self.registration_url = '/{}registrations/{}/comments/'.format(API_BASE, self.registration._id)

    def test_comments_on_deleted_wikis_are_not_returned(self):
        self._set_up_private_project_with_comment()
        # Delete wiki
        self.private_project.delete_node_wiki(self.wiki.page_name, core.Auth(self.user))
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_not_in(self.comment._id, comment_ids)


class NodeCommentsCreateMixin(object):

    def setUp(self):
        super(NodeCommentsCreateMixin, self).setUp()
        self.user = AuthUserFactory()
        self.read_only_contributor = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

    def _set_up_payload(self, target_id):
        raise NotImplementedError

    def _set_up_private_project_with_private_comment_level(self):
        raise NotImplementedError

    def _set_up_public_project_with_private_comment_level(self):
        raise NotImplementedError

    def _set_up_public_project_with_public_comment_level(self):
        raise NotImplementedError

    def _set_up_private_project_with_public_comment_level(self):
        raise NotImplementedError

    def test_private_node_private_comment_level_logged_in_admin_can_comment(self):
        self._set_up_private_project_with_private_comment_level()
        res = self.app.post_json_api(self.private_url, self.private_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.private_payload['data']['attributes']['content'])

    def test_private_node_private_comment_level_logged_in_read_contributor_can_comment(self):
        self._set_up_private_project_with_private_comment_level()
        res = self.app.post_json_api(self.private_url, self.private_payload, auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.private_payload['data']['attributes']['content'])

    def test_private_node_private_comment_level_non_contributor_cannot_comment(self):
        self._set_up_private_project_with_private_comment_level()
        res = self.app.post_json_api(self.private_url, self.private_payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_private_node_private_comment_level_logged_out_user_cannot_comment(self):
        self._set_up_private_project_with_private_comment_level()
        res = self.app.post_json_api(self.private_url, self.private_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_private_node_with_public_comment_level_admin_can_comment(self):
        """ Test admin contributors can still comment on a private project with comment_level == 'public' """
        self._set_up_private_project_with_public_comment_level()
        res = self.app.post_json_api(self.private_project_public_comments_url,
                                     self.private_project_public_comments_payload,
                                     auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'],
                     self.private_project_public_comments_payload['data']['attributes']['content'])

    def test_private_node_with_public_comment_level_read_only_contributor_can_comment(self):
        """ Test read-only contributors can still comment on a private project with comment_level == 'public' """
        self._set_up_private_project_with_public_comment_level()
        res = self.app.post_json_api(self.private_project_public_comments_url,
                                     self.private_project_public_comments_payload,
                                     auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'],
                     self.private_project_public_comments_payload['data']['attributes']['content'])

    def test_private_node_with_public_comment_level_non_contributor_cannot_comment(self):
        """ Test non-contributors cannot comment on a private project with comment_level == 'public' """
        self._set_up_private_project_with_public_comment_level()
        res = self.app.post_json_api(self.private_project_public_comments_url,
                                     self.private_project_public_comments_payload,
                                     auth=self.non_contributor.auth,
                                     expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_with_public_comment_level_logged_out_user_cannot_comment(self):
        """ Test logged out users cannot comment on a private project with comment_level == 'public' """
        self._set_up_private_project_with_public_comment_level()
        res = self.app.post_json_api(self.private_project_public_comments_url,
                                     self.private_project_public_comments_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_public_project_with_public_comment_level_admin_can_comment(self):
        """ Test admin contributor can still comment on a public project when it is
            configured so any logged-in user can comment (comment_level == 'public') """
        self._set_up_public_project_with_public_comment_level()
        res = self.app.post_json_api(self.public_comments_url, self.public_comment_level_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.public_comment_level_payload['data']['attributes']['content'])

    def test_public_project_with_public_comment_level_read_only_contributor_can_comment(self):
        """ Test read-only contributor can still comment on a public project when it is
            configured so any logged-in user can comment (comment_level == 'public') """
        self._set_up_public_project_with_public_comment_level()
        res = self.app.post_json_api(self.public_comments_url, self.public_comment_level_payload, auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.public_comment_level_payload['data']['attributes']['content'])

    def test_public_project_with_public_comment_level_non_contributor_can_comment(self):
        """ Test non-contributors can comment on a public project when it is
            configured so any logged-in user can comment (comment_level == 'public') """
        self._set_up_public_project_with_public_comment_level()
        res = self.app.post_json_api(self.public_comments_url, self.public_comment_level_payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.public_comment_level_payload['data']['attributes']['content'])

    def test_public_project_with_public_comment_level_logged_out_user_cannot_comment(self):
        """ Test logged out users cannot comment on a public project when it is
            configured so any logged-in user can comment (comment_level == 'public') """
        self._set_up_public_project_with_public_comment_level()
        res = self.app.post_json_api(self.public_comments_url, self.public_comment_level_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_public_node_private_comment_level_admin_can_comment(self):
        """ Test only contributors can comment on a public project when it is
            configured so only contributors can comment (comment_level == 'private') """
        self._set_up_public_project_with_private_comment_level()
        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.public_payload['data']['attributes']['content'])

    def test_public_node_private_comment_level_read_only_contributor_can_comment(self):
        self._set_up_public_project_with_private_comment_level()
        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.public_payload['data']['attributes']['content'])

    def test_public_node_private_comment_level_non_contributor_cannot_comment(self):
        self._set_up_public_project_with_private_comment_level()
        res = self.app.post_json_api(self.public_url, self.public_payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_public_node_private_comment_level_logged_out_user_cannot_comment(self):
        self._set_up_public_project_with_private_comment_level()
        res = self.app.post_json_api(self.public_url, self.public_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')


class TestNodeCommentCreate(NodeCommentsCreateMixin, ApiTestCase):

    def _set_up_payload(self, target_id):
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

    def _set_up_private_project_with_private_comment_level(self):
        self.private_project = ProjectFactory(is_public=False, creator=self.user, comment_level='private')
        self.private_project.add_contributor(self.read_only_contributor, permissions=['read'])
        self.private_project.save()
        self.private_url = '/{}nodes/{}/comments/'.format(API_BASE, self.private_project._id)
        self.private_payload = self._set_up_payload(self.private_project._id)

    def _set_up_public_project_with_private_comment_level(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user, comment_level='private')
        self.public_project.add_contributor(self.read_only_contributor, permissions=['read'])
        self.public_project.save()
        self.public_url = '/{}nodes/{}/comments/'.format(API_BASE, self.public_project._id)
        self.public_payload = self._set_up_payload(self.public_project._id)

    def _set_up_public_project_with_public_comment_level(self):
        """ Public project configured so that any logged-in user can comment."""
        self.project_with_public_comment_level = ProjectFactory(is_public=True, creator=self.user)
        self.project_with_public_comment_level.add_contributor(self.read_only_contributor, permissions=['read'])
        self.project_with_public_comment_level.save()
        self.public_comments_url = '/{}nodes/{}/comments/'.format(API_BASE, self.project_with_public_comment_level._id)
        self.public_comment_level_payload = self._set_up_payload(self.project_with_public_comment_level._id)

    def _set_up_private_project_with_public_comment_level(self):
        self.private_project_with_public_comment_level = ProjectFactory(is_public=False, creator=self.user)
        self.private_project_with_public_comment_level.add_contributor(self.read_only_contributor, permissions=['read'])
        self.private_project_with_public_comment_level.save()
        self.private_project_public_comments_url = '/{}nodes/{}/comments/'.format(API_BASE, self.private_project_with_public_comment_level)
        self.private_project_public_comments_payload = self._set_up_payload(self.private_project_with_public_comment_level._id)

    def test_create_comment_invalid_data(self):
        self._set_up_private_project_with_private_comment_level()
        res = self.app.post_json_api(self.private_url, "Incorrect data", auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_create_comment_no_relationships(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/relationships.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/relationships')

    def test_create_comment_empty_relationships(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {}
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data/relationships.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/relationships')

    def test_create_comment_relationship_is_a_list(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': [{'id': self.private_project._id}]
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Malformed request.")

    def test_create_comment_target_no_data_in_relationships(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
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
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /data.')
        assert_equal(res.json['errors'][0]['source']['pointer'], 'data/relationships/target/data')

    def test_create_comment_no_target_key_in_relationships(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'data': {
                        'type': 'nodes',
                        'id': self.private_project._id
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Malformed request.')

    def test_create_comment_blank_target_id(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
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
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Invalid comment target ''.")

    def test_create_comment_invalid_target_id(self):
        self._set_up_private_project_with_private_comment_level()
        project_id = ProjectFactory()._id
        payload = self._set_up_payload(project_id)
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Invalid comment target \'" + str(project_id) + "\'.")

    def test_create_comment_invalid_target_type(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'Invalid',
                            'id': self.private_project._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'Invalid target type. Expected "nodes", got "Invalid."')

    def test_create_comment_no_target_type_in_relationships(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'id': self.private_project._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Request must include /type.')

    def test_create_comment_no_type(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': '',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': self.private_project._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be blank.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_create_comment_incorrect_type(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'cookies',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': self.private_project._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'Resource identifier does not match server endpoint.')

    def test_create_comment_no_content(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': ''
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': self.private_project._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be blank.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/attributes/content')

    def test_create_comment_trims_whitespace(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': '   '
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': self.private_project._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be blank.')

    def test_create_comment_with_allowed_tags(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': '<em>Cool</em> <strong>Comment</strong>'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': self.private_project._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], payload['data']['attributes']['content'])

    def test_create_comment_exceeds_max_length(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': (''.join(['c' for c in range(osf_settings.COMMENT_MAXLENGTH + 1)]))
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'nodes',
                            'id': self.private_project._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'],
                     'Ensure this field has no more than {} characters.'.format(str(osf_settings.COMMENT_MAXLENGTH)))

    def test_create_comment_invalid_target_node(self):
        url = '/{}nodes/{}/comments/'.format(API_BASE, 'abcde')
        payload = self._set_up_payload('abcde')
        res = self.app.post_json_api(url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')


class TestFileCommentCreate(NodeCommentsCreateMixin, ApiTestCase):

    def _set_up_payload(self, target_id):
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

    def _set_up_private_project_with_private_comment_level(self):
        self.private_project = ProjectFactory(is_public=False, creator=self.user, comment_level='private')
        self.private_project.add_contributor(self.read_only_contributor, permissions=['read'])
        self.private_project.save()
        self.private_url = '/{}nodes/{}/comments/'.format(API_BASE, self.private_project._id)
        self.test_file = test_utils.create_test_file(self.private_project, self.user)
        self.private_payload = self._set_up_payload(self.test_file.get_guid()._id)

    def _set_up_public_project_with_private_comment_level(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user, comment_level='private')
        self.public_project.add_contributor(self.read_only_contributor, permissions=['read'])
        self.public_project.save()
        self.public_url = '/{}nodes/{}/comments/'.format(API_BASE, self.public_project._id)
        self.test_file = test_utils.create_test_file(self.public_project, self.user)
        self.public_payload = self._set_up_payload(self.test_file.get_guid()._id)

    def _set_up_public_project_with_public_comment_level(self):
        """ Public project configured so that any logged-in user can comment."""
        self.project_with_public_comment_level = ProjectFactory(is_public=True, creator=self.user)
        self.project_with_public_comment_level.add_contributor(self.read_only_contributor, permissions=['read'])
        self.project_with_public_comment_level.save()
        self.public_comments_url = '/{}nodes/{}/comments/'.format(API_BASE, self.project_with_public_comment_level._id)
        self.test_file = test_utils.create_test_file(self.project_with_public_comment_level, self.user)
        self.public_comment_level_payload = self._set_up_payload(self.test_file.get_guid()._id)

    def _set_up_private_project_with_public_comment_level(self):
        self.private_project_with_public_comment_level = ProjectFactory(is_public=False, creator=self.user)
        self.private_project_with_public_comment_level.add_contributor(self.read_only_contributor, permissions=['read'])
        self.private_project_with_public_comment_level.save()
        self.private_project_public_comments_url = '/{}nodes/{}/comments/'.format(API_BASE, self.private_project_with_public_comment_level)
        self.test_file = test_utils.create_test_file(self.private_project_with_public_comment_level, self.user)
        self.private_project_public_comments_payload = self._set_up_payload(self.test_file.get_guid()._id)

    def test_create_file_comment_invalid_target_id(self):
        self._set_up_private_project_with_private_comment_level()
        file = test_utils.create_test_file(ProjectFactory(), self.user)
        payload = self._set_up_payload(file._id)
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Invalid comment target \'" + str(file._id) + "\'.")

    def test_create_file_comment_invalid_target_type(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'Invalid',
                            'id': self.test_file.get_guid()._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'Invalid target type. Expected "files", got "Invalid."')


class TestWikiCommentCreate(NodeCommentsCreateMixin, ApiTestCase):

    def _set_up_payload(self, target_id):
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

    def _set_up_private_project_with_private_comment_level(self):
        self.private_project = ProjectFactory(is_public=False, creator=self.user, comment_level='private')
        self.private_project.add_contributor(self.read_only_contributor, permissions=['read'])
        self.private_project.save()
        self.private_url = '/{}nodes/{}/comments/'.format(API_BASE, self.private_project._id)
        self.wiki = NodeWikiFactory(node=self.private_project, user=self.user)
        self.private_payload = self._set_up_payload(self.wiki._id)

    def _set_up_public_project_with_private_comment_level(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user, comment_level='private')
        self.public_project.add_contributor(self.read_only_contributor, permissions=['read'])
        self.public_project.save()
        self.public_url = '/{}nodes/{}/comments/'.format(API_BASE, self.public_project._id)
        self.wiki = NodeWikiFactory(node=self.public_project, user=self.user)
        self.public_payload = self._set_up_payload(self.wiki._id)

    def _set_up_public_project_with_public_comment_level(self):
        """ Public project configured so that any logged-in user can comment."""
        self.project_with_public_comment_level = ProjectFactory(is_public=True, creator=self.user)
        self.project_with_public_comment_level.add_contributor(self.read_only_contributor, permissions=['read'])
        self.project_with_public_comment_level.save()
        self.public_comments_url = '/{}nodes/{}/comments/'.format(API_BASE, self.project_with_public_comment_level._id)
        self.wiki = NodeWikiFactory(node=self.project_with_public_comment_level, user=self.user)
        self.public_comment_level_payload = self._set_up_payload(self.wiki._id)

    def _set_up_private_project_with_public_comment_level(self):
        self.private_project_with_public_comment_level = ProjectFactory(is_public=False, creator=self.user)
        self.private_project_with_public_comment_level.add_contributor(self.read_only_contributor, permissions=['read'])
        self.private_project_with_public_comment_level.save()
        self.private_project_public_comments_url = '/{}nodes/{}/comments/'.format(API_BASE, self.private_project_with_public_comment_level)
        self.wiki = NodeWikiFactory(node=self.private_project_with_public_comment_level, user=self.user)
        self.private_project_public_comments_payload = self._set_up_payload(self.wiki._id)

    def test_create_wiki_comment_invalid_target_id(self):
        self._set_up_private_project_with_private_comment_level()
        wiki = NodeWikiFactory(node=ProjectFactory(), user=self.user)
        payload = self._set_up_payload(wiki._id)
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Invalid comment target \'" + str(wiki._id) + "\'.")

    def test_create_wiki_comment_invalid_target_type(self):
        self._set_up_private_project_with_private_comment_level()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                },
                'relationships': {
                    'target': {
                        'data': {
                            'type': 'Invalid',
                            'id': self.wiki._id
                        }
                    }
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'Invalid target type. Expected "wiki", got "Invalid."')


class TestCommentRepliesCreate(NodeCommentsCreateMixin, ApiTestCase):

    def _set_up_payload(self, comment_id):
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

    def _set_up_private_project_with_private_comment_level(self):
        self.private_project = ProjectFactory.create(is_public=False, creator=self.user, comment_level='private')
        self.private_project.add_contributor(self.read_only_contributor, permissions=['read'], save=True)
        self.comment = CommentFactory(node=self.private_project, user=self.user)
        self.private_url = '/{}nodes/{}/comments/'.format(API_BASE, self.private_project._id)
        self.private_payload = self._set_up_payload(self.comment._id)

    def _set_up_public_project_with_private_comment_level(self):
        self.public_project = ProjectFactory.create(is_public=True, creator=self.user, comment_level='private')
        self.public_project.add_contributor(self.read_only_contributor, permissions=['read'], save=True)
        self.public_comment = CommentFactory(node=self.public_project, user=self.user)
        self.public_url = '/{}nodes/{}/comments/'.format(API_BASE, self.public_project._id)
        self.public_payload = self._set_up_payload(self.public_comment._id)

    def _set_up_private_project_with_public_comment_level(self):
        self.private_project_with_public_comment_level = ProjectFactory(is_public=False, creator=self.user)
        self.private_project_with_public_comment_level.add_contributor(self.read_only_contributor, permissions=['read'], save=True)
        comment = CommentFactory(node=self.private_project_with_public_comment_level, user=self.user)
        reply = CommentFactory(node=self.private_project_with_public_comment_level, target=Guid.load(comment._id), user=self.user)
        self.private_project_public_comments_url = '/{}nodes/{}/comments/'.format(API_BASE, self.private_project_with_public_comment_level._id)
        self.private_project_public_comments_payload = self._set_up_payload(reply._id)

    def _set_up_public_project_with_public_comment_level(self):
        self.public_project_with_public_comment_level = ProjectFactory(is_public=True, creator=self.user)
        self.public_project_with_public_comment_level.add_contributor(self.read_only_contributor, permissions=['read'], save=True)
        comment = CommentFactory(node=self.public_project_with_public_comment_level, user=self.user)
        reply = CommentFactory(node=self.public_project_with_public_comment_level, target=Guid.load(comment._id), user=self.user)
        self.public_comments_url = '/{}nodes/{}/comments/'.format(API_BASE, self.public_project_with_public_comment_level._id)
        self.public_comment_level_payload = self._set_up_payload(reply._id)

    def test_create_comment_reply_invalid_target_id(self):
        self._set_up_private_project_with_private_comment_level()
        target_comment = CommentFactory(node=ProjectFactory(), user=self.user)
        payload = self._set_up_payload(target_comment._id)
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], "Invalid comment target \'" + str(target_comment._id) + "\'.")


class TestCommentFiltering(ApiTestCase):

    def setUp(self):
        super(TestCommentFiltering, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.comment = CommentFactory(node=self.project, user=self.user, page='node')
        self.deleted_comment = CommentFactory(node=self.project, user=self.user, is_deleted=True, page='node')
        self.base_url = '/{}nodes/{}/comments/'.format(API_BASE, self.project._id)

        self.formatted_date_created = self.comment.date_created.strftime('%Y-%m-%dT%H:%M:%S.%f')
        self.comment.edit('Edited comment', auth=core.Auth(self.user), save=True)
        self.formatted_date_modified = self.comment.date_modified.strftime('%Y-%m-%dT%H:%M:%S.%f')

    def test_node_comments_with_no_filter_returns_all_comments(self):
        res = self.app.get(self.base_url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)

    def test_filtering_for_deleted_comments(self):
        url = self.base_url + '?filter[deleted]=True'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_true(res.json['data'][0]['attributes']['deleted'])

    def test_filtering_for_non_deleted_comments(self):
        url = self.base_url + '?filter[deleted]=False'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_false(res.json['data'][0]['attributes']['deleted'])

    def test_filtering_comments_created_before_date(self):
        url = self.base_url + '?filter[date_created][lt]={}'.format(self.formatted_date_created)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 0)

    def test_filtering_comments_created_on_date(self):
        url = self.base_url + '?filter[date_created][eq]={}'.format(self.formatted_date_created)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_filtering_comments_created_on_or_before_date(self):
        url = self.base_url + '?filter[date_created][lte]={}'.format(self.formatted_date_created)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_filtering_comments_created_after_date(self):
        url = self.base_url + '?filter[date_created][gt]={}'.format(self.formatted_date_created)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_filtering_comments_created_on_or_after_date(self):
        url = self.base_url + '?filter[date_created][gte]={}'.format(self.formatted_date_created)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)

    def test_filtering_comments_modified_before_date(self):
        url = self.base_url + '?filter[date_modified][lt]={}'.format(self.formatted_date_modified)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_filtering_comments_modified_on_date(self):
        url = self.base_url + '?filter[date_modified][eq]={}'.format(self.formatted_date_modified)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)

    def test_filtering_comments_modified_after_date(self):
        url = self.base_url + '?filter[date_modified][gt]={}'.format(self.formatted_date_modified)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 0)

    def test_filtering_by_target_node(self):
        url = self.base_url + '?filter[target]=' + str(self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)
        assert_in(self.project._id, res.json['data'][0]['relationships']['target']['links']['related']['href'])
        assert_in(self.project._id, res.json['data'][1]['relationships']['target']['links']['related']['href'])

    def test_filtering_by_target_no_results(self):
        url = self.base_url + '?filter[target]=' + 'fakeid'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 0)

    def test_filtering_for_comment_replies(self):
        reply = CommentFactory(node=self.project, user=self.user, target=Guid.load(self.comment._id))
        url = self.base_url + '?filter[target]=' + str(self.comment._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_in(self.comment._id, res.json['data'][0]['relationships']['target']['links']['related']['href'])

    def test_filtering_by_target_file(self):
        test_file = test_utils.create_test_file(self.project, self.user)
        target = test_file.get_guid()
        file_comment = CommentFactory(node=self.project, user=self.user, target=target)
        url = self.base_url + '?filter[target]=' + str(target._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_in(test_file._id, res.json['data'][0]['relationships']['target']['links']['related']['href'])

    def test_filtering_by_target_wiki(self):
        test_wiki = NodeWikiFactory(node=self.project, user=self.user)
        wiki_comment = CommentFactory(node=self.project, user=self.user, target=Guid.load(test_wiki._id), page='wiki')
        url = self.base_url + '?filter[target]=' + str(test_wiki._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_in(test_wiki.page_name, res.json['data'][0]['relationships']['target']['links']['related']['href'])

    def test_filtering_by_page_node(self):
        url = self.base_url + '?filter[page]=node'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 2)
        assert_equal('node', res.json['data'][0]['attributes']['page'])
        assert_equal('node', res.json['data'][1]['attributes']['page'])

    def test_filtering_by_page_files(self):
        test_file = test_utils.create_test_file(self.project, self.user)
        file_comment = CommentFactory(node=self.project, user=self.user, target=test_file.get_guid(), page='files')
        url = self.base_url + '?filter[page]=files'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal('files', res.json['data'][0]['attributes']['page'])

    def test_filtering_by_page_wiki(self):
        test_wiki = NodeWikiFactory(node=self.project, user=self.user)
        wiki_comment = CommentFactory(node=self.project, user=self.user, target=Guid.load(test_wiki._id), page='wiki')
        url = self.base_url + '?filter[page]=wiki'
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['data']), 1)
        assert_equal('wiki', res.json['data'][0]['attributes']['page'])
