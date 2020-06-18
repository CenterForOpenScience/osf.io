import mock
import pytest
import responses
from website import settings
from urllib.parse import parse_qs

from osf.models import NodeLog, SpamStatus

from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory
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

    @responses.activate
    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    def test_do_spam_check_true(self, user, request_headers):
        responses.add(
            responses.Response(
                responses.POST,
                'https://none.rest.akismet.com/1.1/comment-check',
                headers={'X-akismet-pro-tip': 'test pro-tip'},
                status=200,
                body='true'
            )
        )

        is_spam = user.do_check_spam(
            author='test-author',
            author_email='test@test.com',
            content='test',
            request_headers=request_headers
        )

        data = parse_qs(responses.calls[0].request.body)

        assert data['comment_author'] == ['test-author']
        assert data['comment_author_email'] == ['test@test.com']
        assert data['blog'] == [settings.DOMAIN]

        assert user.spam_status == SpamStatus.FLAGGED

        assert is_spam
        assert user.spam_pro_tip == 'test pro-tip'

    @responses.activate
    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    def test_confirm_spam(self, user, spam_data):
        user.spam_data = spam_data
        user.save()
        responses.add(
            responses.Response(
                responses.POST,
                'https://none.rest.akismet.com/1.1/submit-spam',
                status=200,
            )
        )

        user.confirm_spam()
        data = parse_qs(responses.calls[0].request.body)

        assert data['comment_author'] == [user.fullname]
        assert data['comment_author_email'] == [user.email]
        assert data['blog'] == [settings.DOMAIN]

        assert user.spam_status == SpamStatus.SPAM
        assert user.spam_data == spam_data

    @responses.activate
    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    def test_confirm_ham(self, user, spam_data):
        user.spam_data = spam_data
        user.spam_status = SpamStatus.SPAM
        user.save()
        responses.add(
            responses.Response(
                responses.POST,
                'https://none.rest.akismet.com/1.1/submit-ham',
                status=200,
            )
        )

        user.confirm_ham(save=True)

        data = parse_qs(responses.calls[0].request.body)

        assert data['comment_author'] == [user.fullname]
        assert data['comment_author_email'] == [user.email]
        assert data['blog'] == [settings.DOMAIN]

        assert user.spam_status == SpamStatus.HAM
        assert user.spam_data == spam_data

    @responses.activate
    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    def test_revert_spam(self, user, node, spam_data):
        user.spam_data = spam_data
        user.save()
        responses.add(
            responses.Response(
                responses.POST,
                'https://none.rest.akismet.com/1.1/submit-spam',
                status=200,
            )
        )
        responses.add(
            responses.Response(
                responses.POST,
                'https://none.rest.akismet.com/1.1/submit-ham',
                status=200,
            )
        )

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
