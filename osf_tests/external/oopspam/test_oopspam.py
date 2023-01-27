import mock
import responses

import pytest
from website import settings

from osf_tests.factories import (
    fake,
    AuthUserFactory,
)
from osf.models.spam import SpamStatus


@pytest.mark.django_db
class TestUserSpamOOPSpam:

    @pytest.fixture
    def user(self):
        return AuthUserFactory()

    def test_get_spam_content(self, user):
        schools_list = []
        expected_content = ''

        for _ in range(2):
            institution = fake.company()
            degree = fake.catch_phrase()
            schools_list.append({
                'degree': degree,
                'institution': institution
            })
            expected_content += '{} {} '.format(degree, institution)
        saved_fields = {'schools': schools_list}

        spam_content = user._get_spam_content(saved_fields)
        assert spam_content == expected_content.strip()

    @mock.patch('osf.external.oopspam.client.OOPSpamClient')
    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    @mock.patch.object(settings, 'OOPSPAM_APIKEY', 'FFFFFF')
    @mock.patch.object(settings, 'OOPSPAM_ENABLED', True)
    @pytest.mark.enable_enqueue_task
    def test_do_check_spam(self, mock_get_oopspam_client, user):
        new_mock = mock.MagicMock()
        new_mock.check_content = mock.MagicMock(return_value=(True, None))
        mock_get_oopspam_client.return_value = new_mock

        suspicious_content = 'spam eggs sausage and spam'
        with mock.patch('osf.models.user.OSFUser._get_spam_content', mock.Mock(return_value=suspicious_content)):
            with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
                rsps.add(responses.POST, f'https://oopspam.p.rapidapi.com/v1/spamdetection', status=200, json={'Score': 6})
                user.do_check_spam(
                    author=user.fullname,
                    author_email=user.username,
                    content=suspicious_content,
                    request_headers={'Referrer': 'Woo', 'User-Agent': 'yay', 'Remote-Addr': 'ok'}
                )
            user.refresh_from_db()

        assert user.spam_data['content'] == suspicious_content
        assert user.spam_data['author'] == user.fullname
        assert user.spam_data['author_email'] == user.username

    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    @mock.patch.object(settings, 'OOPSPAM_APIKEY', 'FFFFFF')
    @mock.patch('osf.models.OSFUser.do_check_spam')
    def test_check_spam(self, mock_do_check_spam, user):

        # test check_spam for other saved fields
        with mock.patch('osf.models.OSFUser._get_spam_content', mock.Mock(return_value='some content!')):
            assert user.check_spam(saved_fields={'fullname': 'Dusty Rhodes'}, request_headers=None) is False
            assert mock_do_check_spam.call_count == 0

        # test check spam for correct saved_fields
        with mock.patch('osf.models.OSFUser._get_spam_content', mock.Mock(return_value='some content!')):
            user.check_spam(saved_fields={'schools': ['one']}, request_headers=None)
            assert mock_do_check_spam.call_count == 1


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

    @pytest.mark.enable_enqueue_task
    def test_do_spam_check_true(self, mock_oopspam, user, request_headers):
        body = '{"Score":3,"Details":{"isContentSpam":"spam","numberOfSpamWords":5}}'

        mock_oopspam.add(
            responses.POST,
            'https://oopspam.p.rapidapi.com/v1/spamdetection',
            status=200,
            body=body
        )
        assert user.spam_status == SpamStatus.UNKNOWN

        user.do_check_spam(
            author='test-author',
            author_email='test@test.com',
            content='test',
            request_headers=request_headers
        )
        user.refresh_from_db()
        assert user.spam_status == SpamStatus.FLAGGED

    @pytest.mark.enable_enqueue_task
    def test_do_spam_check_false(self, mock_oopspam, user, request_headers):
        body = '{"Score":2,"Details":{"isContentSpam":"spam","numberOfSpamWords":5}}'

        mock_oopspam.add(
            responses.POST,
            'https://oopspam.p.rapidapi.com/v1/spamdetection',
            status=200,
            body=body
        )
        assert user.spam_status == SpamStatus.UNKNOWN

        user.do_check_spam(
            author='test-author',
            author_email='test@test.com',
            content='test',
            request_headers=request_headers
        )

        assert user.spam_status == SpamStatus.UNKNOWN
