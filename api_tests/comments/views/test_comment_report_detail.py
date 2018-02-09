from django.utils import timezone
import mock
import pytest

from addons.wiki.tests.factories import NodeWikiFactory
from api.base.settings.defaults import API_BASE
from api_tests import utils as test_utils
from osf.models import Guid
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    CommentFactory,
)


@pytest.mark.django_db
class ReportDetailViewMixin(object):

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def payload(self, user):
        return {
            'data': {
                'id': user._id,
                'type': 'comment_reports',
                'attributes': {
                    'category': 'spam',
                    'message': 'Spam is delicious.'
                }
            }
        }

    # check if all necessary features are setup in subclass
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
    def public_project(self):
        raise NotImplementedError

    @pytest.fixture()
    def public_comment(self):
        raise NotImplementedError

    @pytest.fixture()
    def public_url(self):
        raise NotImplementedError

    def test_private_node_view_report_detail_auth_misc(
            self, app, user, contributor, non_contrib, private_url):
        # test_private_node_reporting_contributor_can_view_report_detail
        res = app.get(private_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == user._id

        # test_private_node_reported_contributor_cannot_view_report_detail
        res = app.get(private_url, auth=contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # test_private_node_logged_in_non_contrib_cannot_view_report_detail
        res = app.get(private_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test_private_node_logged_out_contributor_cannot_view_report_detail
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401

    def test_public_node_view_report_detail_auth_misc(
            self, app, user, contributor, non_contrib, public_url):
        # test_public_node_reporting_contributor_can_view_report_detail
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == user._id

        # test_public_node_reported_contributor_cannot_view_report_detail
        res = app.get(public_url, auth=contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # test_public_node_logged_in_non_contrib_cannot_view_other_users_report_detail
        res = app.get(public_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test_public_node_logged_out_contributor_cannot_view_report_detail
        res = app.get(public_url, expect_errors=True)
        assert res.status_code == 401

    def test_public_node_logged_in_non_contrib_reporter_can_view_own_report_detail(
            self, app, non_contrib, public_comment):
        public_comment.reports[non_contrib._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }
        public_comment.save()
        url = '/{}comments/{}/reports/{}/'.format(
            API_BASE, public_comment._id, non_contrib._id)
        res = app.get(url, auth=non_contrib.auth)
        assert res.status_code == 200

    def test_private_node_update_report_detail_auth_misc(
            self, app, user, contributor, non_contrib, payload, private_url):
        # test_private_node_reported_contributor_cannot_update_report_detail
        res = app.put_json_api(
            private_url, payload,
            auth=contributor.auth, expect_errors=True
        )
        assert res.status_code == 403

        # test_private_node_logged_in_non_contrib_cannot_update_report_detail
        res = app.put_json_api(
            private_url, payload,
            auth=non_contrib.auth, expect_errors=True
        )
        assert res.status_code == 403

        # test_private_node_logged_out_contributor_cannot_update_detail
        res = app.put_json_api(private_url, payload, expect_errors=True)
        assert res.status_code == 401

        # test_private_node_reporting_contributor_can_update_report_detail
        res = app.put_json_api(private_url, payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == user._id
        assert res.json['data']['attributes']['message'] == payload['data']['attributes']['message']

    def test_public_node_update_report_detail_auth_misc(
            self, app, user, contributor, non_contrib, payload, public_url):
        # test_public_node_reported_contributor_cannot_update_detail
        res = app.put_json_api(
            public_url, payload,
            auth=contributor.auth, expect_errors=True
        )
        assert res.status_code == 403

        # test_public_node_logged_in_non_contrib_cannot_update_other_users_report_detail
        res = app.put_json_api(
            public_url, payload,
            auth=non_contrib.auth, expect_errors=True
        )
        assert res.status_code == 403

        # test_public_node_logged_out_contributor_cannot_update_report_detail
        res = app.put_json_api(public_url, payload, expect_errors=True)
        assert res.status_code == 401

        # test_public_node_reporting_contributor_can_update_detail
        res = app.put_json_api(public_url, payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['id'] == user._id
        assert res.json['data']['attributes']['message'] == payload['data']['attributes']['message']

    def test_public_node_logged_in_non_contrib_reporter_can_update_own_report_detail(
            self, app, non_contrib, public_comment):
        public_comment.reports[non_contrib._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }
        public_comment.save()
        url = '/{}comments/{}/reports/{}/'.format(
            API_BASE, public_comment._id, non_contrib._id)
        payload = {
            'data': {
                'id': non_contrib._id,
                'type': 'comment_reports',
                'attributes': {
                    'category': 'spam',
                    'message': 'Spam is delicious.'
                }
            }
        }
        res = app.put_json_api(url, payload, auth=non_contrib.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['message'] == payload['data']['attributes']['message']

    def test_private_node_delete_report_detail_auth_misc(
            self, app, user, contributor, non_contrib,
            private_project, private_url, comment
    ):
        # test_private_node_reported_contributor_cannot_delete_report_detail
        res = app.delete_json_api(
            private_url, auth=contributor.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        # test_private_node_logged_in_non_contrib_cannot_delete_report_detail
        res = app.delete_json_api(
            private_url, auth=non_contrib.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        # test_private_node_logged_out_contributor_cannot_delete_detail
        res = app.delete_json_api(private_url, expect_errors=True)
        assert res.status_code == 401

        # test_private_node_reporting_contributor_can_delete_report_detail
        comment_new = CommentFactory.build(
            node=private_project,
            user=contributor,
            target=comment.target
        )
        comment_new.reports = {user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }}
        comment_new.save()
        url = '/{}comments/{}/reports/{}/'.format(
            API_BASE, comment_new._id, user._id)
        res = app.delete_json_api(url, auth=user.auth)
        assert res.status_code == 204

    def test_public_node_delete_report_detail_auth_misc(
            self, app, user, contributor, non_contrib, public_url):

        # test_public_node_reported_contributor_cannot_delete_detail
        res = app.delete_json_api(
            public_url, auth=contributor.auth,
            expect_errors=True)
        assert res.status_code == 403

        # test_public_node_logged_in_non_contrib_cannot_delete_other_users_report_detail
        res = app.delete_json_api(
            public_url, auth=non_contrib.auth,
            expect_errors=True)
        assert res.status_code == 403

        # test_public_node_logged_out_contributor_cannot_delete_report_detail
        res = app.delete_json_api(public_url, expect_errors=True)
        assert res.status_code == 401

        # test_public_node_reporting_contributor_can_delete_detail
        res = app.delete_json_api(public_url, auth=user.auth)
        assert res.status_code == 204

    def test_public_node_logged_in_non_contrib_reporter_can_delete_own_report_detail(
            self, app, non_contrib, public_comment):
        public_comment.reports[non_contrib._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }
        public_comment.save()
        url = '/{}comments/{}/reports/{}/'.format(
            API_BASE, public_comment._id, non_contrib._id)
        res = app.delete_json_api(url, auth=non_contrib.auth)
        assert res.status_code == 204


class TestReportDetailView(ReportDetailViewMixin):

    # private_project_comment_reports
    @pytest.fixture()
    def private_project(self, user, contributor):
        private_project = ProjectFactory.create(is_public=False, creator=user)
        private_project.add_contributor(contributor=contributor, save=True)
        return private_project

    @pytest.fixture()
    def comment(self, user, contributor, private_project):
        comment = CommentFactory(node=private_project, user=contributor)
        comment.reports = {user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }}
        comment.save()
        return comment

    @pytest.fixture()
    def private_url(self, user, comment):
        return '/{}comments/{}/reports/{}/'.format(
            API_BASE, comment._id, user._id)

    # public_project_comment_reports
    @pytest.fixture()
    def public_project(self, user, contributor):
        public_project = ProjectFactory.create(is_public=True, creator=user)
        public_project.add_contributor(contributor=contributor, save=True)
        return public_project

    @pytest.fixture()
    def public_comment(self, user, contributor, public_project):
        public_comment = CommentFactory(node=public_project, user=contributor)
        public_comment.reports = {user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }}
        public_comment.save()
        return public_comment

    @pytest.fixture()
    def public_url(self, user, public_comment):
        return '/{}comments/{}/reports/{}/'.format(
            API_BASE, public_comment._id, user._id)


class TestFileCommentReportDetailView(ReportDetailViewMixin):

    # private_project_comment_reports
    @pytest.fixture()
    def private_project(self, user, contributor):
        private_project = ProjectFactory.create(is_public=False, creator=user)
        private_project.add_contributor(contributor=contributor, save=True)
        return private_project

    @pytest.fixture()
    def file(self, user, private_project):
        return test_utils.create_test_file(private_project, user)

    @pytest.fixture()
    def comment(self, user, contributor, private_project, file):
        comment = CommentFactory(
            node=private_project,
            target=file.get_guid(),
            user=contributor)
        comment.reports = {user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }}
        comment.save()
        return comment

    @pytest.fixture()
    def private_url(self, user, comment):
        return '/{}comments/{}/reports/{}/'.format(
            API_BASE, comment._id, user._id)

    # public_project_comment_reports
    @pytest.fixture()
    def public_project(self, user, contributor):
        public_project = ProjectFactory.create(is_public=True, creator=user)
        public_project.add_contributor(contributor=contributor, save=True)
        return public_project

    @pytest.fixture()
    def public_file(self, user, public_project):
        return test_utils.create_test_file(public_project, user)

    @pytest.fixture()
    def public_comment(self, user, contributor, public_project, public_file):
        public_comment = CommentFactory(
            node=public_project,
            target=public_file.get_guid(),
            user=contributor)
        public_comment.reports = {user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }}
        public_comment.save()
        return public_comment

    @pytest.fixture()
    def public_url(self, user, public_comment):
        return '/{}comments/{}/reports/{}/'.format(
            API_BASE, public_comment._id, user._id)


class TestWikiCommentReportDetailView(ReportDetailViewMixin):

    # private_project_comment_reports
    @pytest.fixture()
    def private_project(self, user, contributor):
        private_project = ProjectFactory.create(is_public=False, creator=user)
        private_project.add_contributor(contributor=contributor, save=True)
        return private_project

    @pytest.fixture()
    def wiki(self, user, private_project):
        with mock.patch('osf.models.AbstractNode.update_search'):
            return NodeWikiFactory(node=private_project, user=user)

    @pytest.fixture()
    def comment(self, user, contributor, private_project, wiki):
        comment = CommentFactory(
            node=private_project,
            target=Guid.load(wiki._id),
            user=contributor
        )
        comment.reports = {user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }}
        comment.save()
        return comment

    @pytest.fixture()
    def private_url(self, user, comment):
        return '/{}comments/{}/reports/{}/'.format(
            API_BASE, comment._id, user._id)

    # public_project_comment_reports
    @pytest.fixture()
    def public_project(self, user, contributor):
        public_project = ProjectFactory.create(is_public=True, creator=user)
        public_project.add_contributor(contributor=contributor, save=True)
        return public_project

    @pytest.fixture()
    def public_wiki(self, user, public_project):
        with mock.patch('osf.models.AbstractNode.update_search'):
            return NodeWikiFactory(node=public_project, user=user)

    @pytest.fixture()
    def public_comment(self, user, contributor, public_project, public_wiki):
        public_comment = CommentFactory(
            node=public_project,
            target=Guid.load(public_wiki._id),
            user=contributor
        )
        public_comment.reports = {user._id: {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }}
        public_comment.save()
        return public_comment

    @pytest.fixture()
    def public_url(self, user, public_comment):
        return '/{}comments/{}/reports/{}/'.format(
            API_BASE, public_comment._id, user._id)
