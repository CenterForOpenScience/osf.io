from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.factories import ProjectFactory, AuthUserFactory, CommentFactory, RegistrationFactory


class TestCommentDetailView(ApiTestCase):
    def setUp(self):
        super(TestCommentDetailView, self).setUp()
        self.user = AuthUserFactory()
        self.contributor = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

    def _set_up_private_project_with_comment(self):
        self.private_project = ProjectFactory.build(is_public=False, creator=self.user)
        self.private_project.add_contributor(self.contributor, save=True)
        self.comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.user)
        self.private_url = '/{}comments/{}/'.format(API_BASE, self.comment._id)
        self.payload = {
            'data': {
                'id': self.comment._id,
                'type': 'comments',
                'attributes': {
                    'content': 'Updating this comment',
                    'deleted': False
                }
            }
        }

    def _set_up_public_project_with_comment(self):
        self.public_project = ProjectFactory.build(is_public=True, creator=self.user)
        self.public_project.add_contributor(self.contributor, save=True)
        self.public_comment = CommentFactory(node=self.public_project, target=self.public_project, user=self.user)
        self.public_url = '/{}comments/{}/'.format(API_BASE, self.public_comment._id)
        self.public_comment_payload = {
            'data': {
                'id': self.public_comment._id,
                'type': 'comments',
                'attributes': {
                    'content': 'Updating this comment',
                    'deleted': False
                }
            }
        }

    def _set_up_registration_with_comment(self):
        self.registration = RegistrationFactory(creator=self.user)
        self.registration_comment = CommentFactory(node=self.registration, user=self.user)
        self.registration_url = '/{}comments/{}/'.format(API_BASE, self.registration_comment._id)

    def test_private_node_logged_in_contributor_can_view_comment(self):
        self._set_up_private_project_with_comment()
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.comment._id, res.json['data']['id'])
        assert_equal(self.comment.content, res.json['data']['attributes']['content'])

    def test_private_node_logged_in_non_contributor_cannot_view_comment(self):
        self._set_up_private_project_with_comment()
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_user_cannot_view_comment(self):
        self._set_up_private_project_with_comment()
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_logged_in_contributor_can_view_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.public_comment._id, res.json['data']['id'])
        assert_equal(self.public_comment.content, res.json['data']['attributes']['content'])

    def test_public_node_logged_in_non_contributor_can_view_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.public_comment._id, res.json['data']['id'])
        assert_equal(self.public_comment.content, res.json['data']['attributes']['content'])

    def test_public_node_logged_out_user_can_view_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(self.public_comment._id, res.json['data']['id'])
        assert_equal(self.public_comment.content, res.json['data']['attributes']['content'])

    def test_registration_logged_in_contributor_can_view_comment(self):
        self._set_up_registration_with_comment()
        res = self.app.get(self.registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.registration_comment._id, res.json['data']['id'])
        assert_equal(self.registration_comment.content, res.json['data']['attributes']['content'])

    def test_comment_has_user_link(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['user']['links']['related']['href']
        expected_url = '/{}users/{}/'.format(API_BASE, self.user._id)
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)

    def test_comment_has_node_link(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['node']['links']['related']['href']
        expected_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)

    def test_comment_has_target_link_with_correct_type(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['target']['links']['related']['href']
        expected_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        target_type = res.json['data']['relationships']['target']['links']['related']['meta']['type']
        expected_type = 'node'
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)
        assert_equal(target_type, expected_type)

    def test_comment_has_replies_link(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['replies']['links']['self']['href']
        expected_url = '/{}comments/{}/replies/'.format(API_BASE, self.public_comment)
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)

    def test_comment_has_reports_link(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['reports']['links']['related']['href']
        expected_url = '/{}comments/{}/reports/'.format(API_BASE, self.public_comment)
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)

    def test_private_node_only_logged_in_contributor_commenter_can_update_comment(self):
        self._set_up_private_project_with_comment()
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.payload['data']['attributes']['content'], res.json['data']['attributes']['content'])

    def test_private_node_logged_in_non_contributor_cannot_update_comment(self):
        self._set_up_private_project_with_comment()
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_user_cannot_update_comment(self):
        self._set_up_private_project_with_comment()
        res = self.app.put_json_api(self.private_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_only_contributor_commenter_can_update_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.put_json_api(self.public_url, self.public_comment_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.public_comment_payload['data']['attributes']['content'], res.json['data']['attributes']['content'])

    def test_public_node_contributor_cannot_update_other_users_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.put_json_api(self.public_url, self.public_comment_payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_non_contributor_cannot_update_other_users_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.put_json_api(self.public_url, self.public_comment_payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_out_user_cannot_update_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.put_json_api(self.public_url, self.public_comment_payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_non_contributor_commenter_can_update_comment(self):
        project = ProjectFactory(is_public=True, comment_level='public')
        comment = CommentFactory(node=project, target=project, user=self.non_contributor)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'content': 'Updating this comment',
                    'deleted': False
                }
            }
        }
        res = self.app.put_json_api(url, payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(payload['data']['attributes']['content'], res.json['data']['attributes']['content'])

    def test_private_node_only_logged_in_contributor_commenter_can_delete_comment(self):
        self._set_up_private_project_with_comment()
        comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.user)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': True
                }
            }
        }
        res = self.app.patch_json_api(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_true(res.json['data']['attributes']['deleted'])
        assert_equal(res.json['data']['attributes']['content'], comment.content)

    def test_private_node_contributor_cannot_delete_other_users_comment(self):
        self._set_up_private_project_with_comment()
        comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.user)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': True
                }
            }
        }
        res = self.app.patch_json_api(url, payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_non_contributor_cannot_delete_comment(self):
        self._set_up_private_project_with_comment()
        comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.user)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': True
                }
            }
        }
        res = self.app.patch_json_api(url, payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_user_cannot_delete_comment(self):
        self._set_up_private_project_with_comment()
        comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.user)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': True
                }
            }
        }
        res = self.app.patch_json_api(url, payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_private_node_only_logged_in_contributor_commenter_can_undelete_comment(self):
        self._set_up_private_project_with_comment()
        comment = CommentFactory.build(node=self.private_project, target=self.private_project, user=self.user)
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': False
                }
            }
        }
        res = self.app.patch_json_api(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_false(res.json['data']['attributes']['deleted'])
        assert_equal(res.json['data']['attributes']['content'], comment.content)

    def test_private_node_contributor_cannot_undelete_other_users_comment(self):
        self._set_up_private_project_with_comment()
        comment = CommentFactory.build(node=self.private_project, target=self.private_project, user=self.user)
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': False
                }
            }
        }
        res = self.app.patch_json_api(url, payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_non_contributor_cannot_undelete_comment(self):
        self._set_up_private_project_with_comment()
        comment = CommentFactory.build(node=self.private_project, target=self.private_project, user=self.user)
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': False
                }
            }
        }
        res = self.app.patch_json_api(url, payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_user_cannot_undelete_comment(self):
        self._set_up_private_project_with_comment()
        comment = CommentFactory.build(node=self.private_project, target=self.private_project, user=self.user)
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': False
                }
            }
        }
        res = self.app.patch_json_api(url, payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_only_logged_in_contributor_commenter_can_delete_comment(self):
        public_project = ProjectFactory(is_public=True, creator=self.user)
        comment = CommentFactory(node=public_project, target=public_project, user=self.user)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': True
                }
            }
        }
        res = self.app.patch_json_api(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_true(res.json['data']['attributes']['deleted'])
        assert_equal(res.json['data']['attributes']['content'], comment.content)

    def test_public_node_contributor_cannot_delete_other_users_comment(self):
        public_project = ProjectFactory(is_public=True, creator=self.user)
        comment = CommentFactory(node=public_project, target=public_project, user=self.user)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': True
                }
            }
        }
        res = self.app.patch_json_api(url, payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_non_contributor_cannot_delete_other_users_comment(self):
        public_project = ProjectFactory(is_public=True, creator=self.user)
        comment = CommentFactory(node=public_project, target=public_project, user=self.user)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': True
                }
            }
        }
        res = self.app.patch_json_api(url, payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_out_user_cannot_delete_comment(self):
        public_project = ProjectFactory(is_public=True, creator=self.user)
        comment = CommentFactory(node=public_project, target=public_project, user=self.user)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': True
                }
            }
        }
        res = self.app.patch_json_api(url, payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_non_contributor_commenter_can_delete_comment(self):
        project = ProjectFactory(is_public=True, comment_level='public')
        comment = CommentFactory(node=project, target=project, user=self.non_contributor)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'id': comment._id,
                'type': 'comments',
                'attributes': {
                    'deleted': True
                }
            }
        }
        res = self.app.patch_json_api(url, payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_true(res.json['data']['attributes']['deleted'])
        assert_equal(res.json['data']['attributes']['content'], comment.content)

    def test_private_node_only_logged_in_commenter_can_view_deleted_comment(self):
        self._set_up_private_project_with_comment()
        comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.user)
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['content'], comment.content)

    def test_private_node_contributor_cannot_see_other_users_deleted_comment(self):
        self._set_up_private_project_with_comment()
        comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.user)
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = self.app.get(url, auth=self.contributor.auth)
        assert_equal(res.status_code, 200)
        assert_is_none(res.json['data']['attributes']['content'])

    def test_private_node_logged_out_user_cannot_see_deleted_comment(self):
        self._set_up_private_project_with_comment()
        comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.user)
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_only_logged_in_commenter_can_view_deleted_comment(self):
        public_project = ProjectFactory(is_public=True, creator=self.user)
        comment = CommentFactory(node=public_project, target=public_project, user=self.user)
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['content'], comment.content)

    def test_public_node_contributor_cannot_view_other_users_deleted_comment(self):
        public_project = ProjectFactory(is_public=True, creator=self.user)
        comment = CommentFactory(node=public_project, target=public_project, user=self.user)
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = self.app.get(url, auth=self.contributor.auth)
        assert_equal(res.status_code, 200)
        assert_is_none(res.json['data']['attributes']['content'])

    def test_public_node_non_contributor_cannot_view_other_users_deleted_comment(self):
        public_project = ProjectFactory(is_public=True, creator=self.user)
        comment = CommentFactory(node=public_project, target=public_project, user=self.user)
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = self.app.get(url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_is_none(res.json['data']['attributes']['content'])

    def test_public_node_logged_out_user_cannot_view_deleted_comments(self):
        public_project = ProjectFactory(is_public=True, creator=self.user)
        comment = CommentFactory(node=public_project, target=public_project, user=self.user)
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_is_none(res.json['data']['attributes']['content'])
