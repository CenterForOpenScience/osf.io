import pytest
import responses
from website import settings
from urllib.parse import parse_qs

from osf.models import NodeLog, SpamStatus

from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    ConferenceFactory
)


@pytest.mark.django_db
class TestSpam:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user, is_public=True)

    @pytest.fixture()
    def node_in_conference(self, user):
        node = ProjectFactory(creator=user, is_public=True)
        con = ConferenceFactory()
        con.auto_check_spam = False
        con.submissions.add(node)
        con.save()
        return node

    @pytest.fixture()
    def request_headers(self):
        return {
            'Remote-Addr': 'test-remote-addr',
            'User-Agent': 'test-user-agent',
            'Referer': 'test-referer',
        }

    @pytest.fixture()
    def spam_data(self, user, request_headers):
        return {
            'headers': request_headers,
            'content': 'test content',
            'author': user.fullname,
            'author_email': user.email
        }

    def test_do_spam_check_true(self, mock_akismet, user, request_headers):
        mock_akismet.add(
            responses.POST,
            'https://none.rest.akismet.com/1.1/comment-check',
            headers={'X-akismet-pro-tip': 'test pro-tip'},
            status=200,
            body='true'
        )

        is_spam = user.do_check_spam(
            author='test-author',
            author_email='test@test.com',
            content='test',
            request_headers=request_headers
        )

        data = parse_qs(mock_akismet.calls[0].request.body)

        assert data['comment_author'] == ['test-author']
        assert data['comment_author_email'] == ['test@test.com']
        assert data['blog'] == [settings.DOMAIN]

        assert user.spam_status == SpamStatus.FLAGGED

        assert is_spam
        assert user.spam_pro_tip == 'test pro-tip'

    def test_confirm_spam(self, mock_akismet, user, spam_data):
        mock_akismet.add(responses.POST, 'https://none.rest.akismet.com/1.1/submit-spam')
        user.spam_data = spam_data
        user.save()

        user.confirm_spam()
        data = parse_qs(mock_akismet.calls[0].request.body)

        assert data['comment_author'] == [user.fullname]
        assert data['comment_author_email'] == [user.email]
        assert data['blog'] == [settings.DOMAIN]

        assert user.spam_status == SpamStatus.SPAM
        assert user.spam_data == spam_data

    def test_confirm_ham(self, mock_akismet, user, spam_data):
        mock_akismet.add(responses.POST, 'https://none.rest.akismet.com/1.1/submit-ham')
        user.spam_data = spam_data
        user.spam_status = SpamStatus.SPAM
        user.save()

        user.confirm_ham(save=True)

        data = parse_qs(mock_akismet.calls[0].request.body)

        assert data['comment_author'] == [user.fullname]
        assert data['comment_author_email'] == [user.email]
        assert data['blog'] == [settings.DOMAIN]

        assert user.spam_status == SpamStatus.HAM
        assert user.spam_data == spam_data

    def test_revert_spam(self, mock_akismet, user, node, spam_data):
        mock_akismet.add(responses.POST, 'https://none.rest.akismet.com/1.1/submit-ham')
        mock_akismet.add(responses.POST, 'https://none.rest.akismet.com/1.1/submit-spam')

        user.spam_data = spam_data
        user.save()

        assert node.is_public

        user.confirm_spam()
        assert user.spam_status == SpamStatus.SPAM
        node.refresh_from_db()

        assert not node.is_public
        assert node.logs.latest().action == NodeLog.CONFIRM_SPAM
        assert node.logs.latest().should_hide

        user.confirm_ham()
        assert user.spam_status == SpamStatus.HAM

        node.refresh_from_db()

        assert node.is_public
        assert node.logs.latest().action == NodeLog.CONFIRM_HAM
        assert node.logs.latest().should_hide

    def test_meetings_skip_spam_check(self, mock_akismet, user, node_in_conference, node, request_headers):
        """
        This test covers an edge case for meetings where users are banned overzealously. This is because users who use
        osf4m to add their account and create a project automatically which creates a false positive for the spam
        filter, this test ensures an exception for spam checking be made in that case.
        :param user:
        :param node:
        :param spam_data:
        :return:
        """
        mock_akismet.add(
            responses.POST,
            'https://none.rest.akismet.com/1.1/comment-check',
            status=200,
            body='true'
        )
        is_spam = node_in_conference.check_spam(user, {'title'}, request_headers)

        assert is_spam is False

        is_spam = node.check_spam(user, {'title'}, request_headers)

        assert is_spam
