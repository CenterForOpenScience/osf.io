from urlparse import urlparse
from nose.tools import *  # flake8: noqa

from framework.auth import core
from framework.guid.model import Guid

from api.base.settings.defaults import API_BASE
from api.base.settings import osf_settings
from api_tests import utils as test_utils
from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    CommentFactory,
    RegistrationFactory,
    PrivateLinkFactory,
    NodeWikiFactory
)


class CommentDetailMixin(object):

    def setUp(self):
        super(CommentDetailMixin, self).setUp()
        self.user = AuthUserFactory()
        self.contributor = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

    def _set_up_payload(self, target_id, content='test', has_content=True):
        payload = {
            'data': {
                'id': target_id,
                'type': 'comments',
                'attributes': {
                    'content': 'Updating this comment',
                    'deleted': False
                }
            }
        }
        if has_content:
            payload['data']['attributes']['content'] = content
        return payload

    def _set_up_private_project_with_comment(self):
        raise NotImplementedError

    def _set_up_public_project_with_comment(self):
        raise NotImplementedError

    def _set_up_registration_with_comment(self):
        raise NotImplementedError

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
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_private_node_logged_out_user_cannot_view_comment(self):
        self._set_up_private_project_with_comment()
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_private_node_user_with_private_link_can_see_comment(self):
        self._set_up_private_project_with_comment()
        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.append(self.private_project)
        private_link.save()
        res = self.app.get('/{}comments/{}/'.format(API_BASE, self.comment._id), {'view_only': private_link.key}, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(self.comment._id, res.json['data']['id'])
        assert_equal(self.comment.content, res.json['data']['attributes']['content'])

    def test_private_node_user_with_anonymous_link_cannot_see_commenter_info(self):
        self._set_up_private_project_with_comment()
        private_link = PrivateLinkFactory(anonymous=True)
        private_link.nodes.append(self.private_project)
        private_link.save()
        res = self.app.get('/{}comments/{}/'.format(API_BASE, self.comment._id), {'view_only': private_link.key})
        assert_equal(res.status_code, 200)
        assert_equal(self.comment._id, res.json['data']['id'])
        assert_equal(self.comment.content, res.json['data']['attributes']['content'])
        assert_not_in('user', res.json['data']['relationships'])

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

    def test_public_node_user_with_private_link_can_view_comment(self):
        self._set_up_public_project_with_comment()
        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.append(self.public_project)
        private_link.save()
        res = self.app.get('/{}comments/{}/'.format(API_BASE, self.public_comment._id), {'view_only': private_link.key}, expect_errors=True)
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

    def test_comment_has_replies_link(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['replies']['links']['self']['href']
        expected_url = '/{}nodes/{}/comments/?filter[target]={}'.format(API_BASE, self.public_project._id, self.public_comment._id)
        assert_equal(res.status_code, 200)
        assert_in(expected_url, url)

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
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_private_node_logged_out_user_cannot_update_comment(self):
        self._set_up_private_project_with_comment()
        res = self.app.put_json_api(self.private_url, self.payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_public_node_only_contributor_commenter_can_update_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.put_json_api(self.public_url, self.public_comment_payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(self.public_comment_payload['data']['attributes']['content'], res.json['data']['attributes']['content'])

    def test_public_node_contributor_cannot_update_other_users_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.put_json_api(self.public_url, self.public_comment_payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_public_node_non_contributor_cannot_update_other_users_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.put_json_api(self.public_url, self.public_comment_payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_public_node_logged_out_user_cannot_update_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.put_json_api(self.public_url, self.public_comment_payload, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_update_comment_cannot_exceed_max_length(self):
        self._set_up_private_project_with_comment()
        content = ''.join(['c' for c in range(osf_settings.COMMENT_MAXLENGTH + 1)])
        payload = self._set_up_payload(self.comment._id, content=content)
        res = self.app.put_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'],
                     'Ensure this field has no more than {} characters.'.format(str(osf_settings.COMMENT_MAXLENGTH)))

    def test_update_comment_cannot_be_empty(self):
        self._set_up_private_project_with_comment()
        payload = self._set_up_payload(self.comment._id, content='')
        res = self.app.put_json_api(self.private_url, payload, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'This field may not be blank.')

    def test_private_node_only_logged_in_contributor_commenter_can_delete_comment(self):
        self._set_up_private_project_with_comment()
        res = self.app.delete_json_api(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 204)

    def test_private_node_contributor_cannot_delete_other_users_comment(self):
        self._set_up_private_project_with_comment()
        res = self.app.delete_json_api(self.private_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_private_node_non_contributor_cannot_delete_comment(self):
        self._set_up_private_project_with_comment()
        res = self.app.delete_json_api(self.private_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_private_node_logged_out_user_cannot_delete_comment(self):
        self._set_up_private_project_with_comment()
        res = self.app.delete_json_api(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_private_node_user_cannot_delete_already_deleted_comment(self):
        self._set_up_private_project_with_comment()
        self.comment.is_deleted = True
        self.comment.save()
        res = self.app.delete_json_api(self.private_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Comment already deleted.')

    def test_private_node_only_logged_in_contributor_commenter_can_undelete_comment(self):
        self._set_up_private_project_with_comment()
        self.comment.is_deleted = True
        self.comment.save()
        url = '/{}comments/{}/'.format(API_BASE, self.comment._id)
        payload = self._set_up_payload(self.comment._id, has_content=False)
        res = self.app.patch_json_api(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_false(res.json['data']['attributes']['deleted'])
        assert_equal(res.json['data']['attributes']['content'], self.comment.content)

    def test_private_node_contributor_cannot_undelete_other_users_comment(self):
        self._set_up_private_project_with_comment()
        self.comment.is_deleted = True
        self.comment.save()
        url = '/{}comments/{}/'.format(API_BASE, self.comment._id)
        payload = self._set_up_payload(self.comment._id, has_content=False)
        res = self.app.patch_json_api(url, payload, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_non_contributor_cannot_undelete_comment(self):
        self._set_up_private_project_with_comment()
        self.comment.is_deleted = True
        self.comment.save()
        url = '/{}comments/{}/'.format(API_BASE, self.comment._id)
        payload = self._set_up_payload(self.comment._id, has_content=False)
        res = self.app.patch_json_api(url, payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_private_node_logged_out_user_cannot_undelete_comment(self):
        self._set_up_private_project_with_comment()
        self.comment.is_deleted = True
        self.comment.save()
        url = '/{}comments/{}/'.format(API_BASE, self.comment._id)
        payload = self._set_up_payload(self.comment._id, has_content=False)
        res = self.app.patch_json_api(url, payload, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_public_node_only_logged_in_contributor_commenter_can_delete_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.delete_json_api(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 204)

    def test_public_node_contributor_cannot_delete_other_users_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.delete_json_api(self.public_url, auth=self.contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_public_node_non_contributor_cannot_delete_other_users_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.delete_json_api(self.public_url, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_public_node_logged_out_user_cannot_delete_comment(self):
        self._set_up_public_project_with_comment()
        res = self.app.delete_json_api(self.public_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_public_node_user_cannot_delete_already_deleted_comment(self):
        self._set_up_public_project_with_comment()
        self.public_comment.is_deleted = True
        self.public_comment.save()
        res = self.app.delete_json_api(self.public_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['detail'], 'Comment already deleted.')

    def test_private_node_only_logged_in_commenter_can_view_deleted_comment(self):
        self._set_up_private_project_with_comment()
        self.comment.is_deleted = True
        self.comment.save()
        url = '/{}comments/{}/'.format(API_BASE, self.comment._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['content'], self.comment.content)

    def test_private_node_contributor_cannot_see_other_users_deleted_comment(self):
        self._set_up_private_project_with_comment()
        self.comment.is_deleted = True
        self.comment.save()
        url = '/{}comments/{}/'.format(API_BASE, self.comment._id)
        res = self.app.get(url, auth=self.contributor.auth)
        assert_equal(res.status_code, 200)
        assert_is_none(res.json['data']['attributes']['content'])

    def test_private_node_logged_out_user_cannot_see_deleted_comment(self):
        self._set_up_private_project_with_comment()
        self.comment.is_deleted = True
        self.comment.save()
        url = '/{}comments/{}/'.format(API_BASE, self.comment._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_private_node_view_only_link_user_cannot_see_deleted_comment(self):
        self._set_up_private_project_with_comment()
        self.comment.is_deleted = True
        self.comment.save()

        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.append(self.private_project)
        private_link.save()

        res = self.app.get('/{}comments/{}/'.format(API_BASE, self.comment._id), {'view_only': private_link.key}, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_is_none(res.json['data']['attributes']['content'])

    def test_private_node_anonymous_view_only_link_user_cannot_see_deleted_comment(self):
        self._set_up_private_project_with_comment()
        self.comment.is_deleted = True
        self.comment.save()

        anonymous_link = PrivateLinkFactory(anonymous=True)
        anonymous_link.nodes.append(self.private_project)
        anonymous_link.save()

        res = self.app.get('/{}comments/{}/'.format(API_BASE, self.comment._id), {'view_only': anonymous_link.key}, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_is_none(res.json['data']['attributes']['content'])

    def test_public_node_only_logged_in_commenter_can_view_deleted_comment(self):
        self._set_up_public_project_with_comment()
        self.public_comment.is_deleted = True
        self.public_comment.save()
        url = '/{}comments/{}/'.format(API_BASE, self.public_comment._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['content'], self.public_comment.content)

    def test_public_node_contributor_cannot_view_other_users_deleted_comment(self):
        self._set_up_public_project_with_comment()
        self.public_comment.is_deleted = True
        self.public_comment.save()
        url = '/{}comments/{}/'.format(API_BASE, self.public_comment._id)
        res = self.app.get(url, auth=self.contributor.auth)
        assert_equal(res.status_code, 200)
        assert_is_none(res.json['data']['attributes']['content'])

    def test_public_node_non_contributor_cannot_view_other_users_deleted_comment(self):
        self._set_up_public_project_with_comment()
        self.public_comment.is_deleted = True
        self.public_comment.save()
        url = '/{}comments/{}/'.format(API_BASE, self.public_comment._id)
        res = self.app.get(url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_is_none(res.json['data']['attributes']['content'])

    def test_public_node_logged_out_user_cannot_view_deleted_comments(self):
        self._set_up_public_project_with_comment()
        self.public_comment.is_deleted = True
        self.public_comment.save()
        url = '/{}comments/{}/'.format(API_BASE, self.public_comment._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_is_none(res.json['data']['attributes']['content'])

    def test_public_node_view_only_link_user_cannot_see_deleted_comment(self):
        self._set_up_public_project_with_comment()
        self.public_comment.is_deleted = True
        self.public_comment.save()

        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.append(self.public_project)
        private_link.save()

        res = self.app.get('/{}comments/{}/'.format(API_BASE, self.public_comment._id), {'view_only': private_link.key}, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_is_none(res.json['data']['attributes']['content'])


class TestCommentDetailView(CommentDetailMixin, ApiTestCase):

    def _set_up_private_project_with_comment(self):
        self.private_project = ProjectFactory.create(is_public=False, creator=self.user)
        self.private_project.add_contributor(self.contributor, save=True)
        self.comment = CommentFactory(node=self.private_project, user=self.user)
        self.private_url = '/{}comments/{}/'.format(API_BASE, self.comment._id)
        self.payload = self._set_up_payload(self.comment._id)

    def _set_up_public_project_with_comment(self):
        self.public_project = ProjectFactory.create(is_public=True, creator=self.user)
        self.public_project.add_contributor(self.contributor, save=True)
        self.public_comment = CommentFactory(node=self.public_project, user=self.user)
        self.public_url = '/{}comments/{}/'.format(API_BASE, self.public_comment._id)
        self.public_comment_payload = self._set_up_payload(self.public_comment._id)

    def _set_up_registration_with_comment(self):
        self.registration = RegistrationFactory(creator=self.user)
        self.registration_comment = CommentFactory(node=self.registration, user=self.user)
        self.registration_url = '/{}comments/{}/'.format(API_BASE, self.registration_comment._id)

    def test_comment_has_target_link_with_correct_type(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['target']['links']['related']['href']
        expected_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        target_type = res.json['data']['relationships']['target']['links']['related']['meta']['type']
        expected_type = 'nodes'
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)
        assert_equal(target_type, expected_type)

    def test_public_node_non_contributor_commenter_can_update_comment(self):
        project = ProjectFactory(is_public=True, comment_level='public')
        comment = CommentFactory(node=project, user=self.non_contributor)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = self._set_up_payload(comment._id)
        res = self.app.put_json_api(url, payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(payload['data']['attributes']['content'], res.json['data']['attributes']['content'])

    def test_public_node_non_contributor_commenter_cannot_update_own_comment_if_comment_level_private(self):
        project = ProjectFactory(is_public=True, comment_level='public')
        comment = CommentFactory(node=project, user=self.non_contributor)
        project.comment_level = 'private'
        project.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = self._set_up_payload(comment._id)
        res = self.app.put_json_api(url, payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_public_node_non_contributor_commenter_can_delete_comment(self):
        project = ProjectFactory(is_public=True)
        comment = CommentFactory(node=project, user=self.non_contributor)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = self.app.delete_json_api(url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 204)


class TestFileCommentDetailView(CommentDetailMixin, ApiTestCase):

    def _set_up_private_project_with_comment(self):
        self.private_project = ProjectFactory.create(is_public=False, creator=self.user, comment_level='private')
        self.private_project.add_contributor(self.contributor, save=True)
        self.file = test_utils.create_test_file(self.private_project, self.user)
        self.comment = CommentFactory(node=self.private_project, target=self.file.get_guid(), user=self.user)
        self.private_url = '/{}comments/{}/'.format(API_BASE, self.comment._id)
        self.payload = self._set_up_payload(self.comment._id)

    def _set_up_public_project_with_comment(self):
        self.public_project = ProjectFactory.create(is_public=True, creator=self.user, comment_level='private')
        self.public_project.add_contributor(self.contributor, save=True)
        self.public_file = test_utils.create_test_file(self.public_project, self.user)
        self.public_comment = CommentFactory(node=self.public_project, target=self.public_file.get_guid(), user=self.user)
        self.public_url = '/{}comments/{}/'.format(API_BASE, self.public_comment._id)
        self.public_comment_payload = self._set_up_payload(self.public_comment._id)

    def _set_up_registration_with_comment(self):
        self.registration = RegistrationFactory(creator=self.user, comment_level='private')
        self.registration_file = test_utils.create_test_file(self.registration, self.user)
        self.registration_comment = CommentFactory(node=self.registration, target=self.registration_file.get_guid(), user=self.user)
        self.registration_url = '/{}comments/{}/'.format(API_BASE, self.registration_comment._id)

    def test_file_comment_has_target_link_with_correct_type(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['target']['links']['related']['href']
        expected_url = '/{}files/{}/'.format(API_BASE, self.public_file._id)
        target_type = res.json['data']['relationships']['target']['links']['related']['meta']['type']
        expected_type = 'files'
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)
        assert_equal(target_type, expected_type)

    def test_public_node_non_contributor_commenter_can_update_file_comment(self):
        project = ProjectFactory(is_public=True)
        test_file = test_utils.create_test_file(project, project.creator)
        comment = CommentFactory(node=project, target=test_file.get_guid(), user=self.non_contributor)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = self._set_up_payload(comment._id)
        res = self.app.put_json_api(url, payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(payload['data']['attributes']['content'], res.json['data']['attributes']['content'])

    def test_public_node_non_contributor_commenter_cannot_update_own_file_comment_if_comment_level_private(self):
        project = ProjectFactory(is_public=True)
        test_file = test_utils.create_test_file(project, project.creator)
        comment = CommentFactory(node=project, target=test_file.get_guid(), user=self.non_contributor)
        project.comment_level = 'private'
        project.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = self._set_up_payload(comment._id)
        res = self.app.put_json_api(url, payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_public_node_non_contributor_commenter_can_delete_file_comment(self):
        project = ProjectFactory(is_public=True, comment_level='public')
        test_file = test_utils.create_test_file(project, project.creator)
        comment = CommentFactory(node=project, target=test_file.get_guid(), user=self.non_contributor)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = self.app.delete_json_api(url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 204)

    def test_comment_detail_for_deleted_file_is_not_returned(self):
        self._set_up_private_project_with_comment()
        # Delete commented file
        osfstorage = self.private_project.get_addon('osfstorage')
        root_node = osfstorage.get_root()
        root_node.delete(self.file)
        res = self.app.get(self.private_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)


class TestWikiCommentDetailView(CommentDetailMixin, ApiTestCase):

    def _set_up_private_project_with_comment(self):
        self.private_project = ProjectFactory.create(is_public=False, creator=self.user, comment_level='private')
        self.private_project.add_contributor(self.contributor, save=True)
        self.wiki = NodeWikiFactory(node=self.private_project, user=self.user)
        self.comment = CommentFactory(node=self.private_project, target=Guid.load(self.wiki._id), user=self.user)
        self.private_url = '/{}comments/{}/'.format(API_BASE, self.comment._id)
        self.payload = self._set_up_payload(self.comment._id)

    def _set_up_public_project_with_comment(self):
        self.public_project = ProjectFactory.create(is_public=True, creator=self.user, comment_level='private')
        self.public_project.add_contributor(self.contributor, save=True)
        self.public_wiki = NodeWikiFactory(node=self.public_project, user=self.user)
        self.public_comment = CommentFactory(node=self.public_project, target=Guid.load(self.public_wiki._id), user=self.user)
        self.public_url = '/{}comments/{}/'.format(API_BASE, self.public_comment._id)
        self.public_comment_payload = self._set_up_payload(self.public_comment._id)

    def _set_up_registration_with_comment(self):
        self.registration = RegistrationFactory(creator=self.user, comment_level='private')
        self.registration_wiki = NodeWikiFactory(node=self.registration, user=self.user)
        self.registration_comment = CommentFactory(node=self.registration, target=Guid.load(self.registration_wiki._id), user=self.user)
        self.registration_url = '/{}comments/{}/'.format(API_BASE, self.registration_comment._id)

    def test_wiki_comment_has_target_link_with_correct_type(self):
        self._set_up_public_project_with_comment()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['target']['links']['related']['href']
        expected_url = self.public_wiki.get_absolute_url()
        target_type = res.json['data']['relationships']['target']['links']['related']['meta']['type']
        expected_type = 'wiki'
        assert_equal(res.status_code, 200)
        assert_equal(url, expected_url)
        assert_equal(target_type, expected_type)

    def test_public_node_non_contributor_commenter_can_update_wiki_comment(self):
        project = ProjectFactory(is_public=True)
        test_wiki = NodeWikiFactory(node=project, user=self.user)
        comment = CommentFactory(node=project, target=Guid.load(test_wiki), user=self.non_contributor)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = self._set_up_payload(comment._id)
        res = self.app.put_json_api(url, payload, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(payload['data']['attributes']['content'], res.json['data']['attributes']['content'])

    def test_public_node_non_contributor_commenter_cannot_update_own_wiki_comment_if_comment_level_private(self):
        project = ProjectFactory(is_public=True)
        test_wiki = NodeWikiFactory(node=project, user=self.user)
        comment = CommentFactory(node=project, target=Guid.load(test_wiki), user=self.non_contributor)
        project.comment_level = 'private'
        project.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = self._set_up_payload(comment._id)
        res = self.app.put_json_api(url, payload, auth=self.non_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')

    def test_public_node_non_contributor_commenter_can_delete_wiki_comment(self):
        project = ProjectFactory(is_public=True, comment_level='public')
        test_wiki = NodeWikiFactory(node=project, user=self.user)
        comment = CommentFactory(node=project, target=Guid.load(test_wiki), user=self.non_contributor)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = self.app.delete_json_api(url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 204)

    def test_comment_detail_for_deleted_wiki_is_not_returned(self):
        self._set_up_private_project_with_comment()
        # Delete commented wiki page
        self.private_project.delete_node_wiki(self.wiki.page_name, core.Auth(self.user))
        res = self.app.get(self.private_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
