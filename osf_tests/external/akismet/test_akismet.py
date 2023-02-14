import mock
import pytest
import responses
from urllib.parse import parse_qs

from osf_tests.factories import (
    fake,
    AuthUserFactory,
    ProjectFactory,
    ConferenceFactory
)
from osf.models import NodeLog, SpamStatus

from website import settings


@pytest.mark.django_db
class TestUserSpamAkismet:

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

    @pytest.mark.enable_enqueue_task
    def test_do_check_spam(self, user, mock_akismet):
        suspicious_content = 'spam eggs sausage and spam'
        user.spam_data = {'Referrer': 'Woo', 'User-Agent': 'yay', 'Remote-Addr': 'ok'}
        user.save()
        with mock.patch('osf.models.user.OSFUser._get_spam_content', mock.Mock(return_value=suspicious_content)):
            with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
                rsps.add(responses.POST, f'https://none.rest.akismet.com/1.1/comment-check', status=200, body='true')
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

        # test do_check_spam for ham user
        user.confirm_ham(train_spam_services=False)
        user.do_check_spam(user, None, None, None)
        user.refresh_from_db()
        assert user.spam_status == SpamStatus.HAM

    @mock.patch.object(settings, 'SPAM_SERVICES_ENABLED', True)
    @mock.patch.object(settings, 'AKISMET_ENABLED', True)
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

    @pytest.mark.enable_enqueue_task
    @mock.patch.object(settings, 'SPAM_SERVICES_ENABLED', True)
    def test_do_spam_check_true(self, mock_akismet, user, request_headers):
        mock_akismet.add(
            responses.POST,
            'https://none.rest.akismet.com/1.1/comment-check',
            headers={'X-akismet-pro-tip': 'test pro-tip'},
            status=200,
            body='true'
        )
        assert user.spam_status == SpamStatus.UNKNOWN

        user.do_check_spam(
            author='test-author',
            author_email='test@test.com',
            content='test',
            request_headers=request_headers
        )

        data = parse_qs(mock_akismet.calls[0].request.body)

        assert data['comment_author'] == ['test-author']
        assert data['comment_author_email'] == ['test@test.com']
        assert data['blog'] == [settings.DOMAIN]

        user.refresh_from_db()
        assert user.spam_status == SpamStatus.FLAGGED
        assert user.spam_pro_tip == 'test pro-tip'

    @pytest.mark.enable_enqueue_task
    def test_confirm_spam(self, mock_akismet, user, spam_data):
        mock_akismet.add(responses.POST, 'https://none.rest.akismet.com/1.1/submit-spam')
        user.spam_data = spam_data
        user.save()

        user.confirm_spam()
        assert user.spam_status == SpamStatus.SPAM
        assert user.spam_data == spam_data

    @pytest.mark.enable_enqueue_task
    def test_confirm_ham(self, mock_akismet, user, spam_data):
        mock_akismet.add(responses.POST, 'https://none.rest.akismet.com/1.1/submit-ham')
        user.spam_data = spam_data
        user.spam_status = SpamStatus.SPAM
        user.save()

        assert user.is_spam
        assert not user.is_ham

        user.confirm_ham(save=True)

        assert user.is_ham
        assert user.spam_status == SpamStatus.HAM
        assert user.spam_data == spam_data

    @pytest.mark.enable_enqueue_task
    def test_revert_spam(self, mock_akismet, user, node, spam_data):
        mock_akismet.add(responses.POST, 'https://none.rest.akismet.com/1.1/submit-ham')
        mock_akismet.add(responses.POST, 'https://none.rest.akismet.com/1.1/submit-spam')

        user.spam_data = spam_data
        user.save()

        assert node.is_public

        user.confirm_spam()
        assert user.is_spam
        assert not user.is_ham
        assert user.spam_status == SpamStatus.SPAM
        node.refresh_from_db()

        assert not node.is_public
        assert node.logs.latest().action == NodeLog.CONFIRM_SPAM
        assert node.logs.latest().should_hide

        user.confirm_ham()
        assert user.is_ham
        assert not user.is_spam
        assert user.spam_status == SpamStatus.HAM

        node.refresh_from_db()

        assert node.is_public
        assert node.logs.latest().action == NodeLog.CONFIRM_HAM
        assert node.logs.latest().should_hide

    @pytest.mark.enable_enqueue_task
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
        node_in_conference.check_spam(user, {'title'}, request_headers)

        node.refresh_from_db()
        assert node.spam_status == SpamStatus.UNKNOWN

        node.check_spam(user, {'title'}, request_headers)
        node.refresh_from_db()
        assert node.spam_status == SpamStatus.FLAGGED
