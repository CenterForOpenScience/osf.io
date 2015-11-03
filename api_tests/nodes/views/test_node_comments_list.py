# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from framework.auth import core

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
    CommentFactory
)


class TestNodeCommentsList(ApiTestCase):

    def setUp(self):
        super(TestNodeCommentsList, self).setUp()
        self.user = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

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
        self.registration_url = '/{}nodes/{}/comments/'.format(API_BASE, self.registration._id)

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

    def test_return_private_node_comments_logged_in_non_contributor(self):
        self._set_up_private_project_with_comment()
        res = self.app.get(self.private_url, auth=self.non_contributor, expect_errors=True)
        assert_equal(res.status_code, 401)

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
        deleted_comment = CommentFactory(node=self.private_project, user=self.user)
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_in(self.comment._id, comment_ids)
        assert_in(deleted_comment._id, comment_ids)


class TestNodeCommentCreate(ApiTestCase):

    def setUp(self):
        super(TestNodeCommentCreate, self).setUp()
        self.user = AuthUserFactory()
        self.read_only_contributor = AuthUserFactory()
        self.non_contributor = AuthUserFactory()
        self.payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a comment'
                }
            }
        }

    def _set_up_private_project(self):
        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_project.add_contributor(self.read_only_contributor, permissions=['read'])
        self.private_project.save()
        self.private_url = '/{}nodes/{}/comments/'.format(API_BASE, self.private_project._id)

    def _set_up_public_project(self):
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_contributor(self.read_only_contributor, permissions=['read'])
        self.public_project.save()
        self.public_url = '/{}nodes/{}/comments/'.format(API_BASE, self.public_project._id)

    def _set_up_public_project_with_public_comment_level(self):
        """ Public project configured so that any logged-in user can comment."""
        self.project_with_public_comment_level = ProjectFactory(is_public=True, creator=self.user)
        self.project_with_public_comment_level.comment_level = 'public'
        self.project_with_public_comment_level.save()
        self.public_comments_url = '/{}nodes/{}/comments/'.format(API_BASE, self.project_with_public_comment_level._id)

    def test_create_comment_invalid_data(self):
        self._set_up_private_project()
        res = self.app.post_json_api(self.private_url, "Incorrect data", auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_create_comment_no_type(self):
        self._set_up_private_project()
        payload = {
            'data': {
                'type': '',
                'attributes': {
                    'content': 'This is a comment'
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be blank.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_create_comment_incorrect_type(self):
        self._set_up_private_project()
        payload = {
            'data': {
                'type': 'cookies',
                'attributes': {
                    'content': 'This is a comment'
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'Resource identifier does not match server endpoint.')

    def test_create_comment_no_content(self):
        self._set_up_private_project()
        payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': ''
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be blank.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/attributes/content')

    def test_create_comment_invalid_target_node(self):
        url = '/{}nodes/{}/comments/'.format(API_BASE, 'abcde')
        res = self.app.post_json_api(url, self.payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        assert_equal(res.json['errors'][0]['detail'], 'Not found.')

    def test_private_node_logged_in_admin_can_comment(self):
        self._set_up_private_project()
        res = self.app.post_json_api(self.private_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.payload['data']['attributes']['content'])

    def test_private_node_logged_in_read_contributor_can_comment(self):
        self._set_up_private_project()
        res = self.app.post_json_api(self.private_url, self.payload, auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.payload['data']['attributes']['content'])

    def test_private_node_non_contributor_cannot_comment(self):
        self._set_up_private_project()
        res = self.app.post_json_api(self.private_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_user_cannot_comment(self):
        self._set_up_private_project()
        res = self.app.post_json_api(self.private_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_private_node_with_public_comment_level_non_contributor_cannot_comment(self):
        """ Test non-contributors cannot comment on a private project
            with comment_level == 'public' """
        project = ProjectFactory(is_public=False, creator=self.user)
        project.comment_level = 'public'
        project.save()
        url = '/{}nodes/{}/comments/'.format(API_BASE, project._id)
        res = self.app.post_json_api(url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_any_logged_in_user_can_comment(self):
        """ Test non-contributors can comment on a public project when it is
            configured so any logged-in user can comment (comment_level == 'public') """
        self._set_up_public_project_with_public_comment_level()
        res = self.app.post_json_api(self.public_comments_url, self.payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.payload['data']['attributes']['content'])

    def test_public_node_contributor_can_comment(self):
        self._set_up_public_project()
        """ Test only contributors can comment on a public project when it is
            configured so only contributors can comment (comment_level == 'private') """
        res = self.app.post_json_api(self.public_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.payload['data']['attributes']['content'])

    def test_public_node_read_only_contributor_can_comment(self):
        self._set_up_public_project()
        res = self.app.post_json_api(self.public_url, self.payload, auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.payload['data']['attributes']['content'])

    def test_public_node_non_contributor_cannot_comment(self):
        self._set_up_public_project()
        res = self.app.post_json_api(self.public_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_out_user_cannot_comment(self):
        self._set_up_public_project()
        res = self.app.post_json_api(self.public_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)


class TestCommentFiltering(ApiTestCase):

    def setUp(self):
        super(TestCommentFiltering, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.comment = CommentFactory(node=self.project, user=self.user)
        self.deleted_comment = CommentFactory(node=self.project, user=self.user, is_deleted=True)
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
