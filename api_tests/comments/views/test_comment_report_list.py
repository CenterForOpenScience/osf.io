from django.utils import timezone
import mock
import pytest

from addons.wiki.tests.factories import WikiFactory
from api.base.settings.defaults import API_BASE
from api_tests import utils as test_utils
from osf.models import Guid
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    CommentFactory,
)
from rest_framework import exceptions


@pytest.mark.django_db
class CommentReportsMixin(object):

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
                    'message': 'delicious spam'
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

    @pytest.fixture()
    def comment_level(self):
        raise NotImplementedError

    def test_private_node_view_reports_auth_misc(
            self, app, user, contributor, non_contrib, private_url):
        # test_private_node_logged_out_user_cannot_view_reports
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401

        # test_private_node_logged_in_non_contrib_cannot_view_reports
        res = app.get(private_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403

        # test_private_node_only_reporting_user_can_view_reports
        res = app.get(private_url, auth=user.auth)
        assert res.status_code == 200
        report_json = res.json['data']
        report_ids = [report['id'] for report in report_json]
        assert len(report_json) == 1
        assert user._id in report_ids

        # test_private_node_reported_user_does_not_see_report
        res = app.get(private_url, auth=contributor.auth)
        assert res.status_code == 200
        report_json = res.json['data']
        report_ids = [report['id'] for report in report_json]
        assert len(report_json) == 0
        assert contributor._id not in report_ids

    def test_public_node_view_report_auth_misc(
            self, app, user, contributor, non_contrib, public_url):
        # test_public_node_logged_out_user_cannot_view_reports
        res = app.get(public_url, expect_errors=True)
        assert res.status_code == 401

        # test_public_node_only_reporting_contributor_can_view_report
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        report_json = res.json['data']
        report_ids = [report['id'] for report in report_json]
        assert len(report_json) == 1
        assert user._id in report_ids

        # test_public_node_reported_user_does_not_see_report
        res = app.get(public_url, auth=contributor.auth)
        assert res.status_code == 200
        report_json = res.json['data']
        report_ids = [report['id'] for report in report_json]
        assert len(report_json) == 0
        assert contributor._id not in report_ids

        # test_public_node_non_contrib_does_not_see_other_user_reports
        res = app.get(public_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 200
        report_json = res.json['data']
        report_ids = [report['id'] for report in report_json]
        assert len(report_json) == 0
        assert non_contrib._id not in report_ids

    def test_public_node_non_contrib_reporter_can_view_own_report(
            self, app, non_contrib, public_comment, public_url):
        public_comment.reports[non_contrib._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }
        public_comment.save()
        res = app.get(public_url, auth=non_contrib.auth)
        assert res.status_code == 200
        report_json = res.json['data']
        report_ids = [report['id'] for report in report_json]
        assert len(report_json) == 1
        assert non_contrib._id in report_ids

    def test_public_node_private_comment_level_non_contrib_cannot_see_reports(
            self, app, non_contrib, public_project, public_url):
        public_project.comment_level = 'private'
        public_project.save()
        res = app.get(public_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_invalid_report_comment(self, app, user, private_url):
        # test_report_comment_invalid_type
        payload = {
            'data': {
                'type': 'Not a valid type.',
                'attributes': {
                    'category': 'spam',
                    'message': 'delicious spam'
                }
            }
        }
        res = app.post_json_api(
            private_url, payload,
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 409

        # test_report_comment_no_type
        payload = {
            'data': {
                'type': '',
                'attributes': {
                    'category': 'spam',
                    'message': 'delicious spam'
                }
            }
        }
        res = app.post_json_api(
            private_url, payload,
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'This field may not be blank.'
        assert res.json['errors'][0]['source']['pointer'] == '/data/type'

        # test_report_comment_invalid_spam_category
        category = 'Not a valid category'
        payload = {
            'data': {
                'type': 'comment_reports',
                'attributes': {
                    'category': category,
                    'message': 'delicious spam'
                }
            }
        }
        res = app.post_json_api(
            private_url, payload,
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '\"' + \
            category + '\"' + ' is not a valid choice.'

    def test_report_comment_allow_blank_message(
            self, app, user, contributor, private_project, comment):

        comment_new = CommentFactory(
            node=private_project,
            user=contributor,
            target=comment.target)
        url = '/{}comments/{}/reports/'.format(API_BASE, comment_new._id)
        payload = {
            'data': {
                'type': 'comment_reports',
                'attributes': {
                    'category': 'spam',
                    'message': ''
                }
            }
        }
        res = app.post_json_api(url, payload, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['id'] == user._id
        assert res.json['data']['attributes']['message'] == payload['data']['attributes']['message']

    def test_private_node_report_comment_auth_misc(
            self, app, user, contributor,
            non_contrib, private_project,
            private_url, comment, payload
    ):

        # test_private_node_logged_out_user_cannot_report_comment
        res = app.post_json_api(private_url, payload, expect_errors=True)
        assert res.status_code == 401

        # test_private_node_logged_in_non_contrib_cannot_report_comment
        res = app.post_json_api(
            private_url, payload,
            auth=non_contrib.auth, expect_errors=True
        )
        assert res.status_code == 403

        # test_private_node_logged_in_contributor_can_report_comment
        comment_new = CommentFactory(
            node=private_project,
            user=contributor,
            target=comment.target)
        url = '/{}comments/{}/reports/'.format(API_BASE, comment_new._id)
        res = app.post_json_api(url, payload, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['id'] == user._id

    def test_user_cannot_report_comment_condition(
            self, app, user, contributor, private_url, payload):
        # test_user_cannot_report_own_comment
        res = app.post_json_api(
            private_url, payload,
            auth=contributor.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'You cannot report your own comment.'

        # test_user_cannot_report_comment_twice
        # User cannot report the comment again
        res = app.post_json_api(
            private_url, payload,
            auth=user.auth, expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Comment already reported.'

    def test_public_node_report_comment_auth_misc(
            self, app, user, contributor,
            non_contrib, public_project,
            public_url, public_comment, payload
    ):
        # def test_public_node_logged_out_user_cannot_report_comment(self):
        res = app.post_json_api(public_url, payload, expect_errors=True)
        assert res.status_code == 401

    # def test_public_node_contributor_can_report_comment(self):
        comment = CommentFactory(
            node=public_project,
            user=contributor,
            target=public_comment.target)
        url = '/{}comments/{}/reports/'.format(API_BASE, comment._id)
        res = app.post_json_api(url, payload, auth=user.auth)
        assert res.status_code == 201
        assert res.json['data']['id'] == user._id

    # def test_public_node_non_contrib_can_report_comment(self):
        """ Test that when a public project allows any osf user to
            comment (comment_level == 'public), non-contributors
            can also report comments.
        """
        res = app.post_json_api(public_url, payload, auth=non_contrib.auth)
        assert res.status_code == 201
        assert res.json['data']['id'] == non_contrib._id

    def test_public_node_private_comment_level_non_contrib_cannot_report_comment(
            self, app, non_contrib, public_project, public_url):
        public_project.comment_level = 'private'
        public_project.save()
        res = app.get(public_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail


class TestCommentReportsView(CommentReportsMixin):
    # private_project_comment_reports
    @pytest.fixture()
    def private_project(self, user, contributor):
        private_project = ProjectFactory.create(is_public=False, creator=user)
        private_project.add_contributor(contributor=contributor, save=True)
        return private_project

    @pytest.fixture()
    def comment(self, user, contributor, private_project):
        comment = CommentFactory(node=private_project, user=contributor)
        comment.reports = comment.reports or {}
        comment.reports[user._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }
        comment.save()
        return comment

    @pytest.fixture()
    def private_url(self, user, comment):
        return '/{}comments/{}/reports/'.format(API_BASE, comment._id)

    # public_project_comment_reports
    @pytest.fixture()
    def public_project(self, user, contributor):
        public_project = ProjectFactory.create(
            is_public=True, creator=user, comment_level='public')
        public_project.add_contributor(contributor=contributor, save=True)
        return public_project

    @pytest.fixture()
    def public_comment(self, user, contributor, public_project):
        public_comment = CommentFactory(node=public_project, user=contributor)
        public_comment.reports = public_comment.reports or {}
        public_comment.reports[user._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }
        public_comment.save()
        return public_comment

    @pytest.fixture()
    def public_url(self, user, public_comment):
        return '/{}comments/{}/reports/'.format(API_BASE, public_comment._id)


class TestWikiCommentReportsView(CommentReportsMixin):

    # private_project_comment_reports
    @pytest.fixture()
    def private_project(self, user, contributor):
        private_project = ProjectFactory.create(is_public=False, creator=user)
        private_project.add_contributor(contributor=contributor, save=True)
        return private_project

    @pytest.fixture()
    def wiki(self, user, private_project):
        with mock.patch('osf.models.AbstractNode.update_search'):
            return WikiFactory(
                user=user,
                node=private_project,
            )

    @pytest.fixture()
    def comment(self, user, contributor, private_project, wiki):
        comment = CommentFactory(
            node=private_project,
            target=Guid.load(wiki._id),
            user=contributor
        )
        comment.reports = comment.reports or {}
        comment.reports[user._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }
        comment.save()
        return comment

    @pytest.fixture()
    def private_url(self, user, comment):
        return '/{}comments/{}/reports/'.format(API_BASE, comment._id)

    # public_project_comment_reports
    @pytest.fixture()
    def public_project(self, user, contributor):
        public_project = ProjectFactory.create(
            is_public=True, creator=user, comment_level='public')
        public_project.add_contributor(contributor=contributor, save=True)
        return public_project

    @pytest.fixture()
    def public_wiki(self, user, public_project):
        with mock.patch('osf.models.AbstractNode.update_search'):
            return WikiFactory(
                user=user,
                node=public_project,
            )

    @pytest.fixture()
    def public_comment(self, user, contributor, public_project, public_wiki):
        public_comment = CommentFactory(
            node=public_project,
            target=Guid.load(public_wiki._id),
            user=contributor
        )
        public_comment.reports = public_comment.reports or {}
        public_comment.reports[user._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }
        public_comment.save()
        return public_comment

    @pytest.fixture()
    def public_url(self, user, public_comment):
        return '/{}comments/{}/reports/'.format(API_BASE, public_comment._id)


class TestFileCommentReportsView(CommentReportsMixin):

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
        comment.reports = comment.reports or {}
        comment.reports[user._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }
        comment.save()
        return comment

    @pytest.fixture()
    def private_url(self, user, comment):
        return '/{}comments/{}/reports/'.format(API_BASE, comment._id)

    # public_project_comment_reports
    @pytest.fixture()
    def public_project(self, user, contributor):
        public_project = ProjectFactory.create(
            is_public=True, creator=user, comment_level='public')
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
        public_comment.reports = public_comment.reports or {}
        public_comment.reports[user._id] = {
            'category': 'spam',
            'text': 'This is spam',
            'date': timezone.now(),
            'retracted': False,
        }
        public_comment.save()
        return public_comment

    @pytest.fixture()
    def public_url(self, user, public_comment):
        return '/{}comments/{}/reports/'.format(API_BASE, public_comment._id)
