import pytest
import responses

from osf.models import SpamStatus

from osf_tests.factories import AuthUserFactory


@pytest.mark.django_db
class TestSpam:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def request_headers(self):
        return {
            'Remote-Addr': 'test-remote-addr',
            'User-Agent': 'test-user-agent',
            'Referer': 'test-referer',
        }

    def test_do_spam_check_true(self, mock_oopspam, user, request_headers):
        body = '{"Score":3,"Details":{"isContentSpam":"spam","numberOfSpamWords":5}}'

        mock_oopspam.add(
            responses.POST,
            'https://oopspam.p.rapidapi.com/v1/spamdetection',
            status=200,
            body=body
        )

        is_spam = user.do_check_spam(
            author='test-author',
            author_email='test@test.com',
            content='test',
            request_headers=request_headers
        )

        assert user.spam_status == SpamStatus.FLAGGED
        assert is_spam

    def test_do_spam_check_false(self, mock_oopspam, user, request_headers):
        body = '{"Score":2,"Details":{"isContentSpam":"spam","numberOfSpamWords":5}}'

        mock_oopspam.add(
            responses.POST,
            'https://oopspam.p.rapidapi.com/v1/spamdetection',
            status=200,
            body=body
        )

        is_spam = user.do_check_spam(
            author='test-author',
            author_email='test@test.com',
            content='test',
            request_headers=request_headers
        )

        assert user.spam_status == SpamStatus.UNKNOWN
        assert not is_spam
