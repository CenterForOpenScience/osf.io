import mock
import pytest
from future.moves.urllib.parse import urlparse

from addons.wiki.tests.factories import WikiFactory
from api.base.settings.defaults import API_BASE
from api.base.settings import osf_settings
from api_tests import utils as test_utils
from framework.auth import core
from osf.models import Guid
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    CommentFactory,
    RegistrationFactory,
    PrivateLinkFactory,
)
from rest_framework import exceptions


@pytest.mark.django_db
@pytest.mark.enable_implicit_clean
class CommentDetailMixin(object):

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    # check if all necessary fixtures are setup by subclass
    @pytest.fixture()
    def private_project(self):
        raise NotImplementedError

    @pytest.fixture()
    def comment(self):
        raise NotImplementedError

    @pytest.fixture()
    def private_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def payload(self):
        raise NotImplementedError

    # public_project_with_comments
    @pytest.fixture()
    def public_project(self):
        raise NotImplementedError

    @pytest.fixture()
    def public_comment(self):
        raise NotImplementedError

    @pytest.fixture()
    def public_comment_reply(self):
        raise NotImplementedError

    @pytest.fixture()
    def public_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def public_comment_payload(self):
        raise NotImplementedError

    # registration_with_comments
    @pytest.fixture()
    def registration(self):
        raise NotImplementedError

    @pytest.fixture()
    def registration_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def registration_comment(self):
        raise NotImplementedError

    @pytest.fixture()
    def comment_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def registration_comment_reply(self):
        raise NotImplementedError

    @pytest.fixture()
    def replies_url(self):
        raise NotImplementedError

    @pytest.fixture()
    def set_up_payload(self):
        def payload(target_id, content='test', has_content=True):
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
        return payload

    def test_private_node_comments_related_auth(
            self, app, user, non_contrib,
            comment, private_url
    ):
        # test_private_node_logged_in_contributor_can_view_comment
        res = app.get(private_url, auth=user.auth)
        assert res.status_code == 200
        assert comment._id == res.json['data']['id']
        assert comment.content == res.json['data']['attributes']['content']

        # def test_private_node_logged_in_non_contrib_cannot_view_comment
        res = app.get(private_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        # def test_private_node_logged_out_user_cannot_view_comment
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    def test_private_node_user_with_private_and_anonymous_link_misc(
            self, app, private_project, comment):
        # def test_private_node_user_with_private_link_can_see_comment
        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.add(private_project)
        private_link.save()
        res = app.get(
            '/{}comments/{}/'.format(API_BASE, comment._id),
            {'view_only': private_link.key}, expect_errors=True
        )
        assert res.status_code == 200
        assert comment._id == res.json['data']['id']
        assert comment.content == res.json['data']['attributes']['content']

        # test_private_node_user_with_anonymous_link_cannot_see_commenter_info
        private_link = PrivateLinkFactory(anonymous=True)
        private_link.nodes.add(private_project)
        private_link.save()
        res = app.get(
            '/{}comments/{}/'.format(API_BASE, comment._id),
            {'view_only': private_link.key}
        )
        assert res.status_code == 200
        assert comment._id == res.json['data']['id']
        assert comment.content == res.json['data']['attributes']['content']
        assert 'user' not in res.json['data']['relationships']

        # test_private_node_user_with_anonymous_link_cannot_see_mention_info
        comment.content = 'test with [@username](userlink) and @mention'
        comment.save()
        res = app.get(
            '/{}comments/{}/'.format(API_BASE, comment._id),
            {'view_only': private_link.key}
        )
        assert res.status_code == 200
        assert comment._id == res.json['data']['id']
        assert 'test with @A User and @mention' == res.json['data']['attributes']['content']

    def test_public_node_comment_can_view_misc(
            self, app, user, non_contrib,
            public_project, public_url,
            public_comment, registration_comment,
            comment_url
    ):
        # test_public_node_logged_in_contributor_can_view_comment
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert public_comment._id == res.json['data']['id']
        assert public_comment.content == res.json['data']['attributes']['content']

        # test_public_node_logged_in_non_contrib_can_view_comment
        res = app.get(public_url, auth=non_contrib.auth)
        assert res.status_code == 200
        assert public_comment._id == res.json['data']['id']
        assert public_comment.content == res.json['data']['attributes']['content']

        # test_public_node_logged_out_user_can_view_comment
        res = app.get(public_url)
        assert res.status_code == 200
        assert public_comment._id == res.json['data']['id']
        assert public_comment.content == res.json['data']['attributes']['content']

        # test_registration_logged_in_contributor_can_view_comment
        res = app.get(comment_url, auth=user.auth)
        assert res.status_code == 200
        assert registration_comment._id == res.json['data']['id']
        assert registration_comment.content == res.json['data']['attributes']['content']

        # test_public_node_user_with_private_link_can_view_comment
        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.add(public_project)
        private_link.save()
        res = app.get(
            '/{}comments/{}/'.format(API_BASE, public_comment._id),
            {'view_only': private_link.key}, expect_errors=True
        )
        assert public_comment._id == res.json['data']['id']
        assert public_comment.content == res.json['data']['attributes']['content']

    def test_comment_has_multiple_links(
            self, app, user, public_url, public_project, public_comment,
            public_comment_reply, comment_url, registration
    ):
        res = app.get(public_url)
        assert res.status_code == 200
        # test_comment_has_user_link
        url_user = res.json['data']['relationships']['user']['links']['related']['href']
        expected_url = '/{}users/{}/'.format(API_BASE, user._id)
        assert urlparse(url_user).path == expected_url

        # test_comment_has_node_link
        url_node = res.json['data']['relationships']['node']['links']['related']['href']
        expected_url = '/{}nodes/{}/'.format(API_BASE, public_project._id)
        assert urlparse(url_node).path == expected_url

        # test_comment_has_replies_link
        url_replies = res.json['data']['relationships']['replies']['links']['related']['href']
        uri = test_utils.urlparse_drop_netloc(url_replies)
        res_uri = app.get(uri)
        assert res_uri.status_code == 200
        assert res_uri.json['data'][0]['type'] == 'comments'

        # test_comment_has_reports_link
        url_reports = res.json['data']['relationships']['reports']['links']['related']['href']
        expected_url = '/{}comments/{}/reports/'.format(
            API_BASE, public_comment._id)
        assert urlparse(url_reports).path == expected_url

        # test_registration_comment_has_node_link
        res = app.get(comment_url, auth=user.auth)
        url = res.json['data']['relationships']['node']['links']['related']['href']
        expected_url = '/{}registrations/{}/'.format(
            API_BASE, registration._id)
        assert res.status_code == 200
        assert urlparse(url).path == expected_url

    def test_private_node_comment_auth_misc(
            self, app, user, non_contrib, private_url, payload):
        # test_private_node_only_logged_in_contributor_commenter_can_update_comment
        res = app.put_json_api(private_url, payload, auth=user.auth)
        assert res.status_code == 200
        assert payload['data']['attributes']['content'] == res.json['data']['attributes']['content']

        # test_private_node_logged_in_non_contrib_cannot_update_comment
        res = app.put_json_api(
            private_url, payload,
            auth=non_contrib.auth, expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        # test_private_node_logged_out_user_cannot_update_comment
        res = app.put_json_api(private_url, payload, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    def test_public_node_comment_update_misc(
            self, app, user, contributor,
            non_contrib, public_url,
            public_comment_payload
    ):
        # test_public_node_only_contributor_commenter_can_update_comment
        res = app.put_json_api(
            public_url, public_comment_payload,
            auth=user.auth
        )
        assert res.status_code == 200
        assert public_comment_payload['data']['attributes']['content'] == res.json['data']['attributes']['content']

        # test_public_node_contributor_cannot_update_other_users_comment
        res = app.put_json_api(
            public_url, public_comment_payload,
            auth=contributor.auth, expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        # test_public_node_non_contrib_cannot_update_other_users_comment
        res = app.put_json_api(
            public_url, public_comment_payload,
            auth=non_contrib.auth, expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        # test_public_node_logged_out_user_cannot_update_comment
        res = app.put_json_api(
            public_url, public_comment_payload,
            expect_errors=True
        )
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    def test_update_comment_misc(
            self, app, user, private_url,
            comment, set_up_payload
    ):
        # test_update_comment_cannot_exceed_max_length
        content = ('c' * (osf_settings.COMMENT_MAXLENGTH + 3))
        payload = set_up_payload(comment._id, content=content)
        res = app.put_json_api(
            private_url, payload,
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert (res.json['errors'][0]['detail'] == 'Ensure this field has no more than {} characters.'.format(
            str(osf_settings.COMMENT_MAXLENGTH)))

        # test_update_comment_cannot_be_empty
        payload = set_up_payload(comment._id, content='')
        res = app.put_json_api(
            private_url, payload,
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be blank.'

    def test_private_node_only_logged_in_contributor_commenter_can_delete_comment(
            self, app, user, private_url):
        res = app.delete_json_api(private_url, auth=user.auth)
        assert res.status_code == 204

    def test_private_node_only_logged_in_contributor_commenter_can_delete_own_reply(
            self, app, user, private_project, comment):
        reply_target = Guid.load(comment._id)
        reply = CommentFactory(
            node=private_project,
            target=reply_target, user=user
        )
        reply_url = '/{}comments/{}/'.format(API_BASE, reply._id)
        res = app.delete_json_api(reply_url, auth=user.auth)
        assert res.status_code == 204

    def test_private_node_only_logged_in_contributor_commenter_can_undelete_own_reply(
            self, app, user, private_project, comment, set_up_payload):
        reply_target = Guid.load(comment._id)
        reply = CommentFactory(
            node=private_project,
            target=reply_target, user=user
        )
        reply_url = '/{}comments/{}/'.format(API_BASE, reply._id)
        reply.is_deleted = True
        reply.save()
        payload = set_up_payload(reply._id, has_content=False)
        res = app.patch_json_api(reply_url, payload, auth=user.auth)
        assert res.status_code == 200
        assert not res.json['data']['attributes']['deleted']
        assert res.json['data']['attributes']['content'] == reply.content

    def test_private_node_cannot_delete_comment_situation(
            self, app, user, contributor, non_contrib, private_url, comment):
        # def
        # test_private_node_contributor_cannot_delete_other_users_comment(self):
        res = app.delete_json_api(
            private_url, auth=contributor.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    # def test_private_node_non_contrib_cannot_delete_comment(self):
        res = app.delete_json_api(
            private_url, auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    # def test_private_node_logged_out_user_cannot_delete_comment(self):
        res = app.delete_json_api(private_url, expect_errors=True)
        assert res.status_code == 401

    # def test_private_node_user_cannot_delete_already_deleted_comment(self):
        comment.is_deleted = True
        comment.save()
        res = app.delete_json_api(
            private_url, auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Comment already deleted.'

    def test_private_node_only_logged_in_contributor_commenter_can_undelete_comment(
            self, app, user, comment, set_up_payload):
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = set_up_payload(comment._id, has_content=False)
        res = app.patch_json_api(url, payload, auth=user.auth)
        assert res.status_code == 200
        assert not res.json['data']['attributes']['deleted']
        assert res.json['data']['attributes']['content'] == comment.content

    def test_private_node_cannot_undelete_comment_situation(
            self, app, contributor, non_contrib, comment, set_up_payload):
        comment.is_deleted = True
        comment.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = set_up_payload(comment._id, has_content=False)

        # test_private_node_contributor_cannot_undelete_other_users_comment
        res = app.patch_json_api(
            url, payload, auth=contributor.auth,
            expect_errors=True)
        assert res.status_code == 403

        # test_private_node_non_contrib_cannot_undelete_comment
        res = app.patch_json_api(
            url, payload, auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

        # test_private_node_logged_out_user_cannot_undelete_comment
        res = app.patch_json_api(url, payload, expect_errors=True)
        assert res.status_code == 401

    def test_public_node_only_logged_in_contributor_commenter_can_delete_comment(
            self, app, user, public_url):
        res = app.delete_json_api(public_url, auth=user.auth)
        assert res.status_code == 204

    def test_public_node_cannot_delete_comment_situations(
            self, app, user, contributor, non_contrib, public_url, public_comment):
        # test_public_node_contributor_cannot_delete_other_users_comment
        res = app.delete_json_api(
            public_url, auth=contributor.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        # test_public_node_non_contrib_cannot_delete_other_users_comment
        res = app.delete_json_api(
            public_url, auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        # test_public_node_logged_out_user_cannot_delete_comment
        res = app.delete_json_api(public_url, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

        # test_public_node_user_cannot_delete_already_deleted_comment
        public_comment.is_deleted = True
        public_comment.save()
        res = app.delete_json_api(
            public_url, auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Comment already deleted.'

    def test_private_node_deleted_comment_auth_misc(
            self, app, user, contributor, comment, private_project):
        comment.is_deleted = True
        comment.save()

        # test_private_node_only_logged_in_commenter_can_view_deleted_comment
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['content'] == comment.content

        # test_private_node_contributor_cannot_see_other_users_deleted_comment
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = app.get(url, auth=contributor.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['content'] is None

        # test_private_node_logged_out_user_cannot_see_deleted_comment
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

        # test_private_node_view_only_link_user_cannot_see_deleted_comment
        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.add(private_project)
        private_link.save()

        res = app.get('/{}comments/{}/'.format(API_BASE, comment._id),
                      {'view_only': private_link.key}, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['content'] is None

        # test_private_node_anonymous_view_only_link_user_cannot_see_deleted_comment
        anonymous_link = PrivateLinkFactory(anonymous=True)
        anonymous_link.nodes.add(private_project)
        anonymous_link.save()

        res = app.get('/{}comments/{}/'.format(API_BASE, comment._id),
                      {'view_only': anonymous_link.key}, expect_errors=True)
        assert res.status_code == 200
        assert res.json['data']['attributes']['content'] is None

    def test_public_node_deleted_comments_auth_misc(
            self, app, user, contributor, non_contrib,
            public_project, public_comment
    ):
        public_comment.is_deleted = True
        public_comment.save()
        url = '/{}comments/{}/'.format(API_BASE, public_comment._id)

        # test_public_node_only_logged_in_commenter_can_view_deleted_comment
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['content'] == public_comment.content

        # test_public_node_contributor_cannot_view_other_users_deleted_comment

        res = app.get(url, auth=contributor.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['content'] is None

        # test_public_node_non_contrib_cannot_view_other_users_deleted_comment
        res = app.get(url, auth=non_contrib.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['content'] is None

        # test_public_node_logged_out_user_cannot_view_deleted_comments
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['data']['attributes']['content'] is None

        # test_public_node_view_only_link_user_cannot_see_deleted_comment
        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.add(public_project)
        private_link.save()

        res = app.get(
            '/{}comments/{}/'.format(
                API_BASE, public_comment._id
            ),
            {'view_only': private_link.key},
            expect_errors=True
        )
        assert res.status_code == 200
        assert res.json['data']['attributes']['content'] is None


class TestCommentDetailView(CommentDetailMixin):

    # private_project_with_comments
    @pytest.fixture()
    def private_project(self, user, contributor):
        private_project = ProjectFactory.create(is_public=False, creator=user)
        private_project.add_contributor(contributor, save=True)
        return private_project

    @pytest.fixture()
    def comment(self, user, private_project):
        return CommentFactory(node=private_project, user=user)

    @pytest.fixture()
    def private_url(self, comment):
        return '/{}comments/{}/'.format(API_BASE, comment._id)

    @pytest.fixture()
    def payload(self, comment, set_up_payload):
        return set_up_payload(comment._id)

    # public_project_with_comments
    @pytest.fixture()
    def public_project(self, user, contributor):
        public_project = ProjectFactory.create(is_public=True, creator=user)
        public_project.add_contributor(contributor, save=True)
        return public_project

    @pytest.fixture()
    def public_comment(self, user, public_project):
        return CommentFactory(node=public_project, user=user)

    @pytest.fixture()
    def public_comment_reply(self, user, public_comment, public_project):
        reply_target = Guid.load(public_comment._id)
        return CommentFactory(
            node=public_project,
            target=reply_target, user=user
        )

    @pytest.fixture()
    def public_url(self, public_comment):
        return '/{}comments/{}/'.format(API_BASE, public_comment._id)

    @pytest.fixture()
    def public_comment_payload(self, public_comment, set_up_payload):
        return set_up_payload(public_comment._id)

    # registration_with_comments
    @pytest.fixture()
    def registration(self, user):
        return RegistrationFactory(creator=user)

    @pytest.fixture()
    def registration_url(self, registration):
        return '/{}registrations/{}/'.format(API_BASE, registration._id)

    @pytest.fixture()
    def registration_comment(self, user, registration):
        return CommentFactory(node=registration, user=user)

    @pytest.fixture()
    def comment_url(self, registration_comment):
        return '/{}comments/{}/'.format(API_BASE, registration_comment._id)

    @pytest.fixture()
    def registration_comment_reply(
            self, user, registration,
            registration_comment
    ):
        reply_target = Guid.load(registration_comment._id)
        return CommentFactory(
            node=registration,
            target=reply_target, user=user
        )

    @pytest.fixture()
    def replies_url(self, registration, registration_comment):
        return '/{}registrations/{}/comments/?filter[target]={}'.format(
            API_BASE, registration._id, registration_comment._id)

    def test_comment_has_target_link_with_correct_type(
            self, app, public_url, public_project):
        res = app.get(public_url)
        url = res.json['data']['relationships']['target']['links']['related']['href']
        expected_url = '/{}nodes/{}/'.format(API_BASE, public_project._id)
        target_type = res.json['data']['relationships']['target']['links']['related']['meta']['type']
        expected_type = 'nodes'
        assert res.status_code == 200
        assert urlparse(url).path == expected_url
        assert target_type == expected_type

    def test_public_node_non_contrib_commenter_can_update_comment(
            self, app, non_contrib, set_up_payload):
        project = ProjectFactory(is_public=True, comment_level='public')
        comment = CommentFactory(node=project, user=non_contrib)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = set_up_payload(comment._id)
        res = app.put_json_api(url, payload, auth=non_contrib.auth)
        assert res.status_code == 200
        assert payload['data']['attributes']['content'] == res.json['data']['attributes']['content']

    def test_public_node_non_contrib_commenter_cannot_update_own_comment_if_comment_level_private(
            self, app, non_contrib, set_up_payload):
        project = ProjectFactory(is_public=True, comment_level='public')
        comment = CommentFactory(node=project, user=non_contrib)
        project.comment_level = 'private'
        project.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = set_up_payload(comment._id)
        res = app.put_json_api(
            url, payload, auth=non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_public_node_non_contrib_commenter_can_delete_comment(
            self, app, non_contrib):
        project = ProjectFactory(is_public=True)
        comment = CommentFactory(node=project, user=non_contrib)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = app.delete_json_api(url, auth=non_contrib.auth)
        assert res.status_code == 204

    def test_registration_comment_has_usable_replies_relationship_link(
            self, app, user, registration_url, registration_comment_reply):
        res = app.get(registration_url, auth=user.auth)
        assert res.status_code == 200
        comments_url = res.json['data']['relationships']['comments']['links']['related']['href']
        comments_uri = test_utils.urlparse_drop_netloc(comments_url)
        comments_res = app.get(comments_uri, auth=user.auth)
        assert comments_res.status_code == 200
        replies_url = comments_res.json['data'][0]['relationships']['replies']['links']['related']['href']
        replies_uri = test_utils.urlparse_drop_netloc(replies_url)
        app.get(replies_uri, auth=user.auth)
        node_url = comments_res.json['data'][0]['relationships']['node']['links']['related']['href']
        node_uri = test_utils.urlparse_drop_netloc(node_url)
        assert node_uri == registration_url

    def test_registration_comment_has_usable_node_relationship_link(
            self, app, user, registration, registration_url,
            registration_comment_reply
    ):
        res = app.get(registration_url, auth=user.auth)
        assert res.status_code == 200
        comments_url = res.json['data']['relationships']['comments']['links']['related']['href']
        comments_uri = test_utils.urlparse_drop_netloc(comments_url)
        comments_res = app.get(comments_uri, auth=user.auth)
        assert comments_res.status_code == 200
        node_url = comments_res.json['data'][0]['relationships']['node']['links']['related']['href']
        node_uri = test_utils.urlparse_drop_netloc(node_url)
        node_res = app.get(node_uri, auth=user.auth)
        assert registration._id in node_res.json['data']['id']


class TestFileCommentDetailView(CommentDetailMixin):
    # private_project_with_comments
    @pytest.fixture()
    def private_project(self, user, contributor):
        private_project = ProjectFactory.create(is_public=False, creator=user)
        private_project.add_contributor(contributor, save=True)
        return private_project

    @pytest.fixture()
    def file(self, user, private_project):
        return test_utils.create_test_file(private_project, user)

    @pytest.fixture()
    def comment(self, user, private_project, file):
        return CommentFactory(
            node=private_project,
            target=file.get_guid(),
            user=user)

    @pytest.fixture()
    def private_url(self, comment):
        return '/{}comments/{}/'.format(API_BASE, comment._id)

    @pytest.fixture()
    def payload(self, comment, set_up_payload):
        return set_up_payload(comment._id)

    # public_project_with_comments
    @pytest.fixture()
    def public_project(self, user, contributor):
        public_project = ProjectFactory.create(
            is_public=True, creator=user, comment_level='private')
        public_project.add_contributor(contributor, save=True)
        return public_project

    @pytest.fixture()
    def public_file(self, user, public_project):
        return test_utils.create_test_file(public_project, user)

    @pytest.fixture()
    def public_comment(self, user, public_project, public_file):
        return CommentFactory(
            node=public_project,
            target=public_file.get_guid(),
            user=user)

    @pytest.fixture()
    def public_comment_reply(self, user, public_comment, public_project):
        reply_target = Guid.load(public_comment._id)
        return CommentFactory(
            node=public_project,
            target=reply_target, user=user
        )

    @pytest.fixture()
    def public_url(self, public_comment):
        return '/{}comments/{}/'.format(API_BASE, public_comment._id)

    @pytest.fixture()
    def public_comment_payload(self, public_comment, set_up_payload):
        return set_up_payload(public_comment._id)

    # registration_with_comments
    @pytest.fixture()
    def registration(self, user):
        return RegistrationFactory(creator=user, comment_level='private')

    @pytest.fixture()
    def registration_file(self, user, registration):
        return test_utils.create_test_file(registration, user)

    @pytest.fixture()
    def registration_comment(self, user, registration, registration_file):
        return CommentFactory(
            node=registration,
            target=registration_file.get_guid(),
            user=user)

    @pytest.fixture()
    def comment_url(self, registration_comment):
        return '/{}comments/{}/'.format(API_BASE, registration_comment._id)

    @pytest.fixture()
    def registration_comment_reply(
            self, user, registration,
            registration_comment
    ):
        reply_target = Guid.load(registration_comment._id)
        return CommentFactory(
            node=registration,
            target=reply_target,
            user=user)

    def test_file_comment_has_target_link_with_correct_type(
            self, app, public_url, public_file):
        res = app.get(public_url)
        url = res.json['data']['relationships']['target']['links']['related']['href']
        expected_url = '/{}files/{}/'.format(API_BASE, public_file._id)
        target_type = res.json['data']['relationships']['target']['links']['related']['meta']['type']
        expected_type = 'files'
        assert res.status_code == 200
        assert urlparse(url).path == expected_url
        assert target_type == expected_type

    def test_public_node_non_contrib_commenter_can_update_file_comment(
            self, app, non_contrib, set_up_payload):
        project = ProjectFactory(is_public=True)
        test_file = test_utils.create_test_file(project, project.creator)
        comment = CommentFactory(
            node=project,
            target=test_file.get_guid(),
            user=non_contrib)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = set_up_payload(comment._id)
        res = app.put_json_api(url, payload, auth=non_contrib.auth)
        assert res.status_code == 200
        assert payload['data']['attributes']['content'] == res.json['data']['attributes']['content']

    def test_public_node_non_contrib_commenter_cannot_update_own_file_comment_if_comment_level_private(
            self, app, non_contrib, set_up_payload):
        project = ProjectFactory(is_public=True)
        test_file = test_utils.create_test_file(project, project.creator)
        comment = CommentFactory(
            node=project,
            target=test_file.get_guid(),
            user=non_contrib)
        project.comment_level = 'private'
        project.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = set_up_payload(comment._id)
        res = app.put_json_api(
            url, payload, auth=non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_public_node_non_contrib_commenter_can_delete_file_comment(
            self, app, non_contrib):
        project = ProjectFactory(is_public=True, comment_level='public')
        test_file = test_utils.create_test_file(project, project.creator)
        comment = CommentFactory(
            node=project,
            target=test_file.get_guid(),
            user=non_contrib)
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = app.delete_json_api(url, auth=non_contrib.auth)
        assert res.status_code == 204

    def test_comment_detail_for_deleted_file_is_not_returned(
            self, app, user, private_project, file, private_url):
        # Delete commented file
        osfstorage = private_project.get_addon('osfstorage')
        osfstorage.get_root()
        file.delete()
        res = app.get(private_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404


class TestWikiCommentDetailView(CommentDetailMixin):
    # private_project_with_comments
    @pytest.fixture()
    def private_project(self, user, contributor):
        private_project = ProjectFactory.create(
            is_public=False, creator=user, comment_level='private')
        private_project.add_contributor(contributor, save=True)
        return private_project

    @pytest.fixture()
    def wiki(self, user, private_project):
        with mock.patch('osf.models.AbstractNode.update_search'):
            wiki = WikiFactory(
                user=user,
                node=private_project,
                page_name='not home'
            )
            return wiki

    @pytest.fixture()
    def comment(self, user, private_project, wiki):
        return CommentFactory(
            node=private_project,
            target=Guid.load(wiki._id),
            user=user
        )

    @pytest.fixture()
    def private_url(self, comment):
        return '/{}comments/{}/'.format(API_BASE, comment._id)

    @pytest.fixture()
    def payload(self, comment, set_up_payload):
        return set_up_payload(comment._id)

    # public_project_with_comments
    @pytest.fixture()
    def public_project(self, user, contributor):
        public_project = ProjectFactory.create(
            is_public=True, creator=user, comment_level='private')
        public_project.add_contributor(contributor, save=True)
        return public_project

    @pytest.fixture()
    def public_wiki(self, user, public_project):
        with mock.patch('osf.models.AbstractNode.update_search'):
            return WikiFactory(
                user=user,
                node=public_project,
            )

    @pytest.fixture()
    def public_comment(self, user, public_project, public_wiki):
        return CommentFactory(
            node=public_project,
            target=Guid.load(public_wiki._id),
            user=user)

    @pytest.fixture()
    def public_comment_reply(self, user, public_comment, public_project):
        reply_target = Guid.load(public_comment._id)
        return CommentFactory(
            node=public_project,
            target=reply_target,
            user=user
        )

    @pytest.fixture()
    def public_url(self, public_comment):
        return '/{}comments/{}/'.format(API_BASE, public_comment._id)

    @pytest.fixture()
    def public_comment_payload(self, public_comment, set_up_payload):
        return set_up_payload(public_comment._id)

    # registration_with_comments
    @pytest.fixture()
    def registration(self, user):
        return RegistrationFactory(creator=user, comment_level='private')

    @pytest.fixture()
    def registration_wiki(self, registration, user):
        with mock.patch('osf.models.AbstractNode.update_search'):
            return WikiFactory(
                user=user,
                node=registration,
            )

    @pytest.fixture()
    def registration_comment(self, user, registration, registration_wiki):
        return CommentFactory(
            node=registration,
            target=Guid.load(registration_wiki._id),
            user=user
        )

    @pytest.fixture()
    def comment_url(self, registration_comment):
        return '/{}comments/{}/'.format(API_BASE, registration_comment._id)

    @pytest.fixture()
    def registration_comment_reply(
            self, user, registration,
            registration_comment
    ):
        reply_target = Guid.load(registration_comment._id)
        return CommentFactory(
            node=registration,
            target=reply_target, user=user
        )

    def test_wiki_comment_has_target_link_with_correct_type(
            self, app, public_url, public_wiki):
        res = app.get(public_url)
        url = res.json['data']['relationships']['target']['links']['related']['href']
        expected_url = public_wiki.get_absolute_url()
        target_type = res.json['data']['relationships']['target']['links']['related']['meta']['type']
        expected_type = 'wiki'
        assert res.status_code == 200
        assert url == expected_url
        assert target_type == expected_type

    def test_public_node_non_contrib_commenter_can_update_wiki_comment(
            self, app, user, non_contrib, set_up_payload):
        project = ProjectFactory(is_public=True)
        wiki_page = WikiFactory(
            user=user,
            node=project,
        )
        comment = CommentFactory(
            node=project,
            target=Guid.load(wiki_page._id),
            user=non_contrib
        )
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = set_up_payload(comment._id)
        res = app.put_json_api(url, payload, auth=non_contrib.auth)
        assert res.status_code == 200
        assert payload['data']['attributes']['content'] == res.json['data']['attributes']['content']

    def test_public_node_non_contrib_commenter_cannot_update_own_wiki_comment_if_comment_level_private(
            self, app, user, non_contrib, set_up_payload):
        project = ProjectFactory(is_public=True)
        wiki_page = WikiFactory(
            user=user,
            node=project,
        )
        comment = CommentFactory(
            node=project,
            target=Guid.load(wiki_page._id),
            user=non_contrib
        )
        project.comment_level = 'private'
        project.save()
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        payload = set_up_payload(comment._id)
        res = app.put_json_api(
            url, payload, auth=non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_public_node_non_contrib_commenter_can_delete_wiki_comment(
            self, app, user, non_contrib):
        project = ProjectFactory(is_public=True, comment_level='public')
        wiki_page = WikiFactory(
            user=user,
            node=project,
        )
        comment = CommentFactory(
            node=project,
            target=Guid.load(wiki_page._id),
            user=non_contrib
        )
        url = '/{}comments/{}/'.format(API_BASE, comment._id)
        res = app.delete_json_api(url, auth=non_contrib.auth)
        assert res.status_code == 204

    def test_comment_detail_for_deleted_wiki_is_not_returned(
            self, app, user, wiki, private_url, private_project):
        # Delete commented wiki page
        wiki.delete(core.Auth(user))
        res = app.get(private_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 404
