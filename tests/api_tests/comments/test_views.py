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

        res = self.app.post_json_api(self.public_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        res = self.app.post_json_api(self.public_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)


class TestCommentReportsView(ApiTestCase):

    def setUp(self):
        super(TestCommentReportsView, self).setUp()
        self.user = AuthUserFactory()
        self.contributor = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_project.add_contributor(contributor=self.contributor, save=True)
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_contributor(contributor=self.contributor, save=True)

        self.comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.contributor)
        self.comment.reports = self.comment.reports or {}
        self.comment.reports[self.user._id] = {'category': 'spam', 'text': 'This is spam'}
        self.comment.save()

        self.public_comment = CommentFactory(node=self.public_project, target=self.public_project, user=self.contributor)
        self.public_comment.reports = self.comment.reports or {}
        self.public_comment.reports[self.user._id] = {'category': 'spam', 'text': 'This is spam'}
        self.public_comment.save()

        self.private_url = '/{}comments/{}/reports/'.format(API_BASE, self.comment._id)
        self.public_url = '/{}comments/{}/reports/'.format(API_BASE, self.public_comment._id)

        self.payload = {
            'data': {
                'type': 'comment_reports',
                'attributes': {
                    'category': 'spam',
                    'message': 'delicious spam'
                }
            }
        }

    def test_private_node_logged_out_user_cannot_view_reports(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_private_node_logged_in_non_contributor_cannot_view_reports(self):
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_only_reporting_user_can_view_reports(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        report_json = res.json['data']
        report_ids = [report['id'] for report in report_json]
        assert_equal(len(report_json), 1)
        assert_in(self.user._id, report_ids)

    def test_private_node_reported_user_does_not_see_report(self):
        res = self.app.get(self.private_url, auth=self.contributor.auth)
        assert_equal(res.status_code, 200)
        report_json = res.json['data']
        report_ids = [report['id'] for report in report_json]
        assert_equal(len(report_json), 0)
        assert_not_in(self.contributor._id, report_ids)

    def test_public_node_only_reporting_contributor_can_view_report(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        report_json = res.json['data']
        report_ids = [report['id'] for report in report_json]
        assert_equal(len(report_json), 1)
        assert_in(self.user._id, report_ids)

    def test_public_node_reported_user_does_not_see_report(self):
        res = self.app.get(self.public_url, auth=self.contributor.auth)
        assert_equal(res.status_code, 200)
        report_json = res.json['data']
        report_ids = [report['id'] for report in report_json]
        assert_equal(len(report_json), 0)
        assert_not_in(self.contributor._id, report_ids)

    def test_public_node_non_contributor_does_not_see_report(self):
        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        report_json = res.json['data']
        report_ids = [report['id'] for report in report_json]
        assert_equal(len(report_json), 0)
        assert_not_in(self.contributor._id, report_ids)

    def test_public_node_logged_out_user_cannot_view_reports(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_non_contributor_reporter_can_view_report(self):
        project = ProjectFactory(is_public=True)
        project.comment_level = 'public'
        project.save()

        comment = CommentFactory(node=project, user=project.creator)
        comment.reports = comment.reports or {}
        comment.reports[self.non_contributor._id] = {'category': 'spam', 'text': 'This is spam.'}
        comment.save()

        url = '/{}comments/{}/reports/'.format(API_BASE, comment._id)

        res = self.app.get(url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        report_json = res.json['data']
        report_ids = [report['id'] for report in report_json]
        assert_equal(len(report_json), 1)
        assert_in(self.non_contributor._id, report_ids)

    def test_report_comment_invalid_type(self):
        payload = {
            'data': {
                'type': 'Not a valid type.',
                'attributes': {
                    'category': 'spam',
                    'message': 'delicious spam'
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 409)

    def test_report_comment_no_type(self):
        payload = {
            'data': {
                'type': '',
                'attributes': {
                    'category': 'spam',
                    'message': 'delicious spam'
                }
            }
        }
        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be blank.')
        assert_equal(res.json['errors'][0]['source']['pointer'], '/data/type')

    def test_report_comment_invalid_spam_category(self):
        payload = {
            'data': {
                'type': 'comment_reports',
                'attributes': {
                    'category': 'Not a valid category',
                    'message': 'delicious spam'
                }
            }
        }

        res = self.app.post_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_report_comment_allow_blank_message(self):
        comment = CommentFactory(node=self.private_project, user=self.contributor)
        url = '/{}comments/{}/reports/'.format(API_BASE, comment._id)
        payload = {
            'data': {
                'type': 'comment_reports',
                'attributes': {
                    'category': 'spam',
                    'message': ''
                }
            }
        }
        res = self.app.post_json_api(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.user._id)
        assert_equal(res.json['data']['attributes']['message'], payload['data']['attributes']['message'])

    def test_private_node_logged_out_user_cannot_report_comment(self):
        res = self.app.post_json_api(self.private_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_private_node_logged_in_non_contributor_cannot_report_comment(self):
        res = self.app.post_json_api(self.private_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_in_contributor_can_report_comment(self):
        comment = CommentFactory(node=self.private_project, user=self.contributor)
        url = '/{}comments/{}/reports/'.format(API_BASE, comment._id)

        res = self.app.post_json_api(url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.user._id)

    def test_user_cannot_report_own_comment(self):
        res = self.app.post_json_api(self.private_url, self.payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_user_cannot_report_comment_twice(self):
        # User reports a comment
        comment = CommentFactory(node=self.private_project, user=self.contributor)
        url = '/{}comments/{}/reports/'.format(API_BASE, comment._id)
        res = self.app.post_json_api(url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)

        # User cannot report the comment again
        res = self.app.post_json_api(url, self.payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_public_node_logged_out_user_cannot_report_comment(self):
        res = self.app.post_json_api(self.public_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_logged_in_non_contributor_cannot_report_comment(self):
        res = self.app.post_json_api(self.public_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_contributor_can_report_comment(self):
        comment = CommentFactory(node=self.public_project, user=self.contributor)
        url = '/{}comments/{}/reports/'.format(API_BASE, comment._id)

        res = self.app.post_json_api(url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.user._id)

    def test_public_node_non_contributor_can_report_comment(self):
        """ Test that when a public project allows any osf user to
            comment (comment_level == 'public), non-contributors
            can also report comments.
        """
        project = ProjectFactory(is_public=True)
        project.comment_level = 'public'
        project.save()
        comment = CommentFactory(node=project, user=project.creator)
        url = '/{}comments/{}/reports/'.format(API_BASE, comment._id)

        res = self.app.post_json_api(url, self.payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 201)
        assert_equal(res.json['data']['id'], self.non_contributor._id)


class TestReportDetailView(ApiTestCase):

    def setUp(self):
        super(TestReportDetailView, self).setUp()
        self.user = AuthUserFactory()
        self.contributor = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

        self.private_project = ProjectFactory(is_public=False, creator=self.user)
        self.private_project.add_contributor(contributor=self.contributor, save=True)
        self.public_project = ProjectFactory(is_public=True, creator=self.user)
        self.public_project.add_contributor(contributor=self.contributor, save=True)

        self.comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.contributor)
        self.comment.reports = {self.user._id: {'category': 'spam', 'text': 'This is spam'}}
        self.comment.save()

        self.public_comment = CommentFactory(node=self.public_project, target=self.public_project, user=self.contributor)
        self.public_comment.reports = {self.user._id: {'category': 'spam', 'text': 'This is spam'}}
        self.public_comment.save()

        self.private_url = '/{}comments/{}/reports/{}/'.format(API_BASE, self.comment._id, self.user._id)
        self.public_url = '/{}comments/{}/reports/{}/'.format(API_BASE, self.public_comment._id, self.user._id)

        self.payload = {
            'data': {
                'id': self.user._id,
                'type': 'comment_reports',
                'attributes': {
                    'category': 'spam',
                    'message': 'Spam is delicious.'
                }
            }
        }

    def test_private_node_reporting_contributor_can_view_report_detail(self):
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)

    def test_private_node_reported_contributor_cannot_view_report_detail(self):
        res = self.app.get(self.private_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_in_non_contributor_cannot_view_report_detail(self):
        res = self.app.get(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_contributor_cannot_view_report_detail(self):
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_reporting_contributor_can_view_report_detail(self):
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)

    def test_public_node_reported_contributor_cannot_view_report_detail(self):
        res = self.app.get(self.public_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_in_non_contributor_cannot_view_report_detail(self):
        """ when comment_level = 'private"""
        res = self.app.get(self.public_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_out_contributor_cannot_view_report_detail(self):
        res = self.app.get(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_logged_in_non_contributor_reporter_can_view_report_detail(self):
        project = ProjectFactory(is_public=True)
        project.comment_level = 'public'
        project.save()
        comment = CommentFactory(node=project, user=project.creator)
        comment.reports = {self.non_contributor._id: {'category': 'spam', 'text': 'This is spam'}}
        comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, comment._id, self.non_contributor._id)
        res = self.app.get(url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)

    def test_private_node_reporting_contributor_can_update_report_detail(self):
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)
        assert_equal(res.json['data']['attributes']['message'], self.payload['data']['attributes']['message'])

    def test_private_node_reported_contributor_cannot_update_report_detail(self):
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_in_non_contributor_cannot_update_report_detail(self):
        res = self.app.put_json_api(self.private_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_contributor_cannot_update_detail(self):
        res = self.app.put_json_api(self.private_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_reporting_contributor_can_update_detail(self):
        res = self.app.put_json_api(self.public_url, self.payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.user._id)
        assert_equal(res.json['data']['attributes']['message'], self.payload['data']['attributes']['message'])

    def test_public_node_reported_contributor_cannot_update_detail(self):
        res = self.app.put_json_api(self.public_url, self.payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_in_non_contributor_cannot_update_report_detail(self):
        """ when comment_level = 'private"""
        res = self.app.put_json_api(self.public_url, self.payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_out_contributor_cannot_update_report_detail(self):
        res = self.app.put_json_api(self.public_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_logged_in_non_contributor_reporter_can_update_report_detail(self):
        project = ProjectFactory(is_public=True)
        project.comment_level = 'public'
        project.save()
        comment = CommentFactory(node=project, user=project.creator)
        comment.reports = {self.non_contributor._id: {'category': 'spam', 'text': 'This is spam'}}
        comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, comment._id, self.non_contributor._id)
        payload = {
            'data': {
                'id': self.non_contributor._id,
                'type': 'comment_reports',
                'attributes': {
                    'category': 'spam',
                    'message': 'Spam is delicious.'
                }
            }
        }
        res = self.app.put_json_api(url, payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['message'], payload['data']['attributes']['message'])

    def test_private_node_reporting_contributor_can_delete_report_detail(self):
        comment = CommentFactory(node=self.private_project, target=self.private_project, user=self.contributor)
        comment.reports = {self.user._id: {'category': 'spam', 'text': 'This is spam'}}
        comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, comment._id, self.user._id)
        res = self.app.delete_json_api(url, auth=self.user.auth)
        assert_equal(res.status_code, 204)

    def test_private_node_reported_contributor_cannot_delete_report_detail(self):
        res = self.app.delete_json_api(self.private_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_in_non_contributor_cannot_delete_report_detail(self):
        res = self.app.delete_json_api(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_contributor_cannot_delete_detail(self):
        res = self.app.delete_json_api(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_reporting_contributor_can_delete_detail(self):
        comment = CommentFactory(node=self.public_project, target=self.private_project, user=self.contributor)
        comment.reports = {self.user._id: {'category': 'spam', 'text': 'This is spam'}}
        comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, comment._id, self.user._id)
        res = self.app.delete_json_api(url, auth=self.user.auth)
        assert_equal(res.status_code, 204)

    def test_public_node_reported_contributor_cannot_delete_detail(self):
        res = self.app.delete_json_api(self.public_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_in_non_contributor_cannot_delete_report_detail(self):
        """ when comment_level = 'private"""
        res = self.app.delete_json_api(self.public_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_public_node_logged_out_contributor_cannot_delete_report_detail(self):
        res = self.app.delete_json_api(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_logged_in_non_contributor_reporter_can_delete_report_detail(self):
        project = ProjectFactory(is_public=True)
        project.comment_level = 'public'
        project.save()
        comment = CommentFactory(node=project, user=project.creator)
        comment.reports = {self.non_contributor._id: {'category': 'spam', 'text': 'This is spam'}}
        comment.save()
        url = '/{}comments/{}/reports/{}/'.format(API_BASE, comment._id, self.non_contributor._id)
        payload = {
            'data': {
                'id': self.non_contributor._id,
                'type': 'comment_reports',
                'attributes': {
                    'category': 'spam',
                    'message': 'Spam is delicious.'
                }
            }
        }
        res = self.app.delete_json_api(url, payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 204)
