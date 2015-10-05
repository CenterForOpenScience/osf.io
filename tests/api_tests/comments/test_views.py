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

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_project.add_contributor(self.contributor, save=True)
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_contributor(self.contributor, save=True)
        self.registration = RegistrationFactory(creator=self.user)

        self.comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.user)
        self.public_comment = CommentFactory(node=self.public_project, target=self.public_project, user=self.user)
        self.registration_comment = CommentFactory(node=self.registration, user=self.user)

        self.private_url = '/{}comments/{}/'.format(API_BASE, self.comment._id)
        self.public_url = '/{}comments/{}/'.format(API_BASE, self.public_comment._id)
        self.registration_url = '/{}comments/{}/'.format(API_BASE, self.registration_comment._id)

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

    def test_private_node_logged_in_contributor_can_view_comment(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.comment._id, res.json['data']['id'])

    def test_private_node_logged_in_non_contributor_cannot_view_comment(self):
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_user_cannot_view_comment(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_logged_in_contributor_can_view_comment(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.public_comment._id, res.json['data']['id'])

    def test_public_node_logged_in_non_contributor_can_view_comment(self):
        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.public_comment._id, res.json['data']['id'])

    def test_public_node_logged_out_user_can_view_comment(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(self.public_comment._id, res.json['data']['id'])

    def test_registration_logged_in_contributor_can_view_comment(self):
        res = self.app.get(self.registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.registration_comment._id, res.json['data']['id'])

    def test_private_node_only_logged_in_contributor_commenter_can_update_comment(self):
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.payload['data']['attributes']['content'], res.json['data']['attributes']['content'])

    def test_private_node_logged_in_non_contributor_cannot_update_comment(self):
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_user_cannot_update_comment(self):
        res = self.app.put_json_api(self.private_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_only_contributor_commenter_can_update_comment(self):
        # Contributor who made the comment
        res = self.app.put_json_api(self.public_url, self.public_comment_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.payload['data']['attributes']['content'], res.json['data']['attributes']['content'])

        # Another contributor on the project who did not make the comment
        res = self.app.put_json_api(self.public_url, self.public_comment_payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        # Non-contributor
        res = self.app.put_json_api(self.public_url, self.public_comment_payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        # Logged-out user
        res = self.app.put_json_api(self.public_url, self.public_comment_payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_non_contributor_commenter_can_update_comment(self):
        project = ProjectFactory(is_public=True)
        project.comment_level = 'public'
        project.save()
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
        assert_equal(self.payload['data']['attributes']['content'], res.json['data']['attributes']['content'])

        res = self.app.put_json_api(url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        res = self.app.put_json_api(url, payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_private_node_only_logged_in_contributor_commenter_can_delete_comment(self):
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

        res = self.app.patch_json_api(url, payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        res = self.app.patch_json_api(url, payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        res = self.app.patch_json_api(url, payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_private_node_only_logged_in_contributor_commenter_can_undelete_comment(self):
        comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.user)
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

        res = self.app.patch_json_api(url, payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        res = self.app.patch_json_api(url, payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        res = self.app.patch_json_api(url, payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_only_logged_in_contributor_commenter_can_delete_comment(self):
        comment = CommentFactory(node=self.public_project, target=self.public_project, user=self.user)
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

        res = self.app.patch_json_api(url, payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        res = self.app.patch_json_api(url, payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        res = self.app.patch_json_api(url, payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_non_contributor_commenter_can_delete_comment(self):
        project = ProjectFactory(is_public=True)
        project.comment_level = 'public'
        project.save()
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

        res = self.app.patch_json_api(url, payload, expect_errors=True)
        assert_equal(res.status_code, 401)


class TestCommentRepliesList(ApiTestCase):

    def setUp(self):
        super(TestCommentRepliesList, self).setUp()
        self.user = AuthUserFactory()
        self.non_contributor = AuthUserFactory()
        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.registration = RegistrationFactory(creator=self.user)

        self.comment = CommentFactory(node=self.private_project, user=self.user)
        self.comment_reply = CommentFactory(node=self.private_project, target=self.comment, user=self.user)

        self.public_comment = CommentFactory(node=self.public_project, user=self.user)
        self.public_comment_reply = CommentFactory(node=self.public_project, target=self.public_comment, user=self.user)

        self.registration_comment = CommentFactory(node=self.registration, user=self.user)
        self.registration_comment_reply = CommentFactory(node=self.registration, target=self.registration_comment, user=self.user)

        self.private_url = '/{}comments/{}/replies/'.format(API_BASE, self.comment._id)
        self.public_url = '/{}comments/{}/replies/'.format(API_BASE, self.public_comment._id)
        self.registration_url = '/{}comments/{}/replies/'.format(API_BASE, self.registration_comment._id)

    def test_return_private_node_comment_replies_logged_out_user(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_return_private_node_comment_replies_logged_in_non_contributor(self):
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_return_private_node_comment_replies_logged_in_contributor(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.comment_reply._id, comment_ids)

    def test_return_public_node_comment_replies_logged_out_user(self):
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.public_comment_reply._id, comment_ids)

    def test_return_public_node_comment_replies_logged_in_non_contributor(self):
        res = self.app.get(self.public_url, auth=self.non_contributor)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.public_comment_reply._id, comment_ids)

    def test_return_public_node_comment_replies_logged_in_contributor(self):
        res = self.app.get(self.public_url, auth=self.user)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.public_comment_reply._id, comment_ids)

    def test_return_registration_comment_replies_logged_in_contributor(self):
        res = self.app.get(self.registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        comment_json = res.json['data']
        comment_ids = [comment['id'] for comment in comment_json]
        assert_equal(len(comment_json), 1)
        assert_in(self.registration_comment_reply._id, comment_ids)


class TestCommentRepliesCreate(ApiTestCase):
    def setUp(self):
        super(TestCommentRepliesCreate, self).setUp()
        self.user = AuthUserFactory()
        self.read_only_contributor = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_project.add_contributor(self.read_only_contributor, permissions=['read'])
        self.private_project.save()
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_contributor(self.read_only_contributor, permissions=['read'])
        self.public_project.save()
        self.registration = RegistrationFactory(creator=self.user)

        self.comment = CommentFactory(node=self.private_project, user=self.user)
        self.public_comment = CommentFactory(node=self.public_project, user=self.user)
        self.registration_comment = CommentFactory(node=self.registration, user=self.user)

        self.private_url = '/{}comments/{}/replies/'.format(API_BASE, self.comment._id)
        self.public_url = '/{}comments/{}/replies/'.format(API_BASE, self.public_comment._id)
        self.registration_url = '/{}comments/{}/replies/'.format(API_BASE, self.registration_comment._id)

        self.payload = {
            'data': {
                'type': 'comments',
                'attributes': {
                    'content': 'This is a reply'
                }
            }
        }

    def test_create_reply_invalid_data(self):
        res = self.app.post_json_api(self.private_url, "Invalid data", auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_create_reply_incorrect_type(self):
        payload = {
            'data': {
                'type': 'Incorrect type',
                'attributes': {
                    'content': 'This is a reply'
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)
        assert_equal(res.json['errors'][0]['detail'], 'Resource identifier does not match server endpoint.')

    def test_create_reply_no_type(self):
        payload = {
            'data': {
                'type': '',
                'attributes': {
                    'content': 'This is a reply'
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be blank.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_create_reply_no_content(self):
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

    def test_private_node_logged_in_admin_can_reply(self):
        res = self.app.post_json_api(self.private_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.payload['data']['attributes']['content'])

    def test_private_node_logged_in_read_only_contributor_can_reply(self):
        res = self.app.post_json_api(self.private_url, self.payload, auth=self.read_only_contributor.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.payload['data']['attributes']['content'])

    def test_private_node_non_contributor_cannot_reply(self):
        res = self.app.post_json_api(self.private_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_user_cannot_reply(self):
        res = self.app.post_json_api(self.private_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_private_node_with_public_comment_level_non_contributor_cannot_reply(self):
        project = ProjectFactory(is_public=False)
        comment = CommentFactory(node=project, user=self.user)
        reply = CommentFactory(node=project, target=comment, user=self.user)
        project.comment_level = 'public'
        project.save()
        url = '/{}comments/{}/replies/'.format(API_BASE, reply._id)

        res = self.app.post_json_api(url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_any_logged_in_user_can_reply(self):
        project = ProjectFactory(is_public=True)
        comment = CommentFactory(node=project, user=self.user)
        reply = CommentFactory(node=project, target=comment, user=self.user)
        project.comment_level = 'public'
        project.save()
        url = '/{}comments/{}/replies/'.format(API_BASE, reply._id)

        res = self.app.post_json_api(url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.payload['data']['attributes']['content'])

        res = self.app.post_json_api(url, self.payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.payload['data']['attributes']['content'])

        res = self.app.post_json_api(self.public_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_only_logged_in_contributors_can_reply(self):
        res = self.app.post_json_api(self.public_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['attributes']['content'], self.payload['data']['attributes']['content'])

        # res = self.app.post_json_api(self.public_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        # assert_equal(res.status_code, 403)

        res = self.app.post_json_api(self.public_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)


class TestReportsView(ApiTestCase):
    pass # List, Create


class TestReportDetailView(ApiTestCase):
    pass # Retrieve, Update, Destroy
