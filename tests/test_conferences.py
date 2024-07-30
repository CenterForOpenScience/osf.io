from unittest import mock

import hmac
import hashlib
from io import BytesIO

import pytest
from django.db import IntegrityError
from furl import furl

from framework.auth import get_or_create_user
from framework.auth.core import Auth

from osf.models import OSFUser, AbstractNode
from addons.wiki.models import WikiVersion
from osf.exceptions import BlockedEmailError
from website import settings
from website.conferences import views
from website.conferences import utils, message
from website.util import api_url_for, web_url_for

from tests.base import OsfTestCase, fake
from osf_tests.factories import ConferenceFactory, ProjectFactory, UserFactory


def assert_absolute(url):
    parsed_domain = furl(settings.DOMAIN)
    parsed_url = furl(url)
    assert parsed_domain.host == parsed_url.host


def assert_equal_urls(first, second):
    parsed_first = furl(first)
    parsed_first.port = None
    parsed_second = furl(second)
    parsed_second.port = None
    assert parsed_first == parsed_second


def create_fake_conference_nodes(n, conference):
    nodes = []
    for i in range(n):
        node = ProjectFactory(is_public=True)
        conference.submissions.add(node)
        node.save()
        nodes.append(node)
    return nodes


def create_fake_conference_nodes_bad_data(conference, n, bad_n, endpoint):
    nodes = []
    for i in range(n):
        node = ProjectFactory(is_public=True)
        conference.submissions.add(node)
        # inject bad data
        if i < bad_n:
            # Delete only contributor
            node.contributor_set.filter(user=node.contributors.first()).delete()
        node.save()
        nodes.append(node)
    return nodes


class TestConferenceUtils(OsfTestCase):

    def test_get_or_create_user_exists(self):
        user = UserFactory()
        fetched, created = get_or_create_user(user.fullname, user.username, is_spam=True)
        assert not created
        assert user._id == fetched._id
        assert 'is_spam' not in fetched.system_tags

    def test_get_or_create_user_not_exists(self):
        fullname = 'Roger Taylor'
        username = 'roger@queen.com'
        fetched, created = get_or_create_user(fullname, username, is_spam=False)
        fetched.save()  # in order to access m2m fields, e.g. tags
        assert created
        assert fetched.fullname == fullname
        assert fetched.username == username
        assert 'is_spam' not in fetched.system_tags

    def test_get_or_create_user_is_spam(self):
        fullname = 'John Deacon'
        username = 'deacon@queen.com'
        fetched, created = get_or_create_user(fullname, username, is_spam=True)
        fetched.save()  # in order to access m2m fields, e.g. tags
        assert created
        assert fetched.fullname == fullname
        assert fetched.username == username
        assert 'is_spam' in fetched.system_tags

    def test_get_or_create_user_with_blocked_domain(self):
        fullname = 'Kanye West'
        username = 'kanye@mailinator.com'
        with pytest.raises(BlockedEmailError) as e:
            get_or_create_user(fullname, username, is_spam=True)
        assert str(e.value) == 'Invalid Email'


class ContextTestCase(OsfTestCase):
    MAILGUN_API_KEY = 'mailkimp'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MAILGUN_API_KEY, cls._MAILGUN_API_KEY = cls.MAILGUN_API_KEY, settings.MAILGUN_API_KEY

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        settings.MAILGUN_API_KEY = cls._MAILGUN_API_KEY

    def make_context(self, method='POST', **kwargs):
        data = {
            'X-Mailgun-Sscore': 0,
            'timestamp': '123',
            'token': 'secret',
            'signature': hmac.new(
                key=settings.MAILGUN_API_KEY.encode(),
                msg='{}{}'.format('123', 'secret').encode(),
                digestmod=hashlib.sha256,
            ).hexdigest(),
        }
        data.update(kwargs.pop('data', {}))
        data = {
            key: value
            for key, value in data.items()
            if value is not None
        }
        return self.app.application.test_request_context(method=method, data=data, **kwargs)


class TestProvisionNode(ContextTestCase):

    def setUp(self):
        super().setUp()
        self.node = ProjectFactory()
        self.user = self.node.creator
        self.conference = ConferenceFactory()
        self.body = 'dragon on my back'
        self.content = b'dragon attack'
        self.attachment = BytesIO(self.content)
        self.recipient = '{}{}-poster@osf.io'.format(
            'test-' if settings.DEV_MODE else '',
            self.conference.endpoint,
        )

    def make_context(self, **kwargs):
        data = {
            'attachment-count': '1',
            'attachment-1': (self.attachment, 'attachment-1'),
            'X-Mailgun-Sscore': 0,
            'recipient': self.recipient,
            'stripped-text': self.body,
        }
        data.update(kwargs.pop('data', {}))
        return super().make_context(data=data, **kwargs)

    def test_provision(self):
        with self.make_context():
            msg = message.ConferenceMessage()
            utils.provision_node(self.conference, msg, self.node, self.user)
        assert self.node.is_public
        assert self.conference.admins.first() in self.node.contributors
        assert 'emailed' in self.node.system_tags
        assert self.conference.endpoint in self.node.system_tags
        assert self.node in self.conference.submissions.all()
        assert 'spam' not in self.node.system_tags

    def test_provision_private(self):
        self.conference.public_projects = False
        self.conference.save()
        with self.make_context():
            msg = message.ConferenceMessage()
            utils.provision_node(self.conference, msg, self.node, self.user)
        assert not self.node.is_public
        assert self.conference.admins.first() in self.node.contributors
        assert 'emailed' in self.node.system_tags
        assert 'spam' not in self.node.system_tags

    def test_provision_spam(self):
        with self.make_context(data={'X-Mailgun-Sscore': message.SSCORE_MAX_VALUE + 1}):
            msg = message.ConferenceMessage()
            utils.provision_node(self.conference, msg, self.node, self.user)
        assert not self.node.is_public
        assert self.conference.admins.first() in self.node.contributors
        assert 'emailed' in self.node.system_tags
        assert 'spam' in self.node.system_tags

    @mock.patch('website.conferences.utils.waterbutler_api_url_for')
    @mock.patch('website.conferences.utils.requests.put')
    def test_upload(self, mock_put, mock_get_url):
        mock_get_url.return_value = 'http://queen.com/'
        file_name = 'hammer-to-fall'
        self.attachment.filename = file_name
        self.attachment.content_type = 'application/json'
        utils.upload_attachment(self.user, self.node, self.attachment)
        mock_get_url.assert_called_with(
            self.node._id,
            'osfstorage',
            _internal=True,
            base_url=self.node.osfstorage_region.waterbutler_url,
            cookie=self.user.get_or_create_cookie().decode(),
            name=file_name
        )
        mock_put.assert_called_with(
            mock_get_url.return_value,
            data=self.content,
        )

    @mock.patch('website.conferences.utils.waterbutler_api_url_for')
    @mock.patch('website.conferences.utils.requests.put')
    def test_upload_no_file_name(self, mock_put, mock_get_url):
        mock_get_url.return_value = 'http://queen.com/'
        self.attachment.filename = ''
        self.attachment.content_type = 'application/json'
        utils.upload_attachment(self.user, self.node, self.attachment)
        mock_get_url.assert_called_with(
            self.node._id,
            'osfstorage',
            _internal=True,
            base_url=self.node.osfstorage_region.waterbutler_url,
            cookie=self.user.get_or_create_cookie().decode(),
            name=settings.MISSING_FILE_NAME,
        )
        mock_put.assert_called_with(
            mock_get_url.return_value,
            data=self.content,
        )

    @mock.patch('website.conferences.utils.upload_attachments')
    def test_add_poster_by_email(self, mock_upload_attachments):
        conference = ConferenceFactory()

        with self.make_context(data={'from': 'bdawk@sb52champs.com', 'subject': 'It\'s PARTY TIME!'}):
            msg = message.ConferenceMessage()
            views.add_poster_by_email(conference, msg)

        user = OSFUser.objects.get(username='bdawk@sb52champs.com')
        assert user.email == 'bdawk@sb52champs.com'
        assert user.fullname == user._id  # user's shouldn't be able to use email as fullname, so we use the guid.


class TestMessage(ContextTestCase):
    PUSH_CONTEXT = False

    def test_verify_signature_valid(self):
        with self.make_context():
            msg = message.ConferenceMessage()
            msg.verify_signature()

    def test_verify_signature_invalid(self):
        with self.make_context(data={'signature': 'fake'}):
            self.app.application.preprocess_request()
            msg = message.ConferenceMessage()
            with pytest.raises(message.ConferenceError):
                msg.verify_signature()

    def test_is_spam_false_missing_headers(self):
        ctx = self.make_context(
            method='POST',
            data={'X-Mailgun-Sscore': message.SSCORE_MAX_VALUE - 1},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert not msg.is_spam

    def test_is_spam_false_all_headers(self):
        ctx = self.make_context(
            method='POST',
            data={
                'X-Mailgun-Sscore': message.SSCORE_MAX_VALUE - 1,
                'X-Mailgun-Dkim-Check-Result': message.DKIM_PASS_VALUES[0],
                'X-Mailgun-Spf': message.SPF_PASS_VALUES[0],
            },
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert not msg.is_spam

    def test_is_spam_true_sscore(self):
        ctx = self.make_context(
            method='POST',
            data={'X-Mailgun-Sscore': message.SSCORE_MAX_VALUE + 1},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert msg.is_spam

    def test_is_spam_true_dkim(self):
        ctx = self.make_context(
            method='POST',
            data={'X-Mailgun-Dkim-Check-Result': message.DKIM_PASS_VALUES[0][::-1]},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert msg.is_spam

    def test_is_spam_true_spf(self):
        ctx = self.make_context(
            method='POST',
            data={'X-Mailgun-Spf': message.SPF_PASS_VALUES[0][::-1]},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert msg.is_spam

    def test_subject(self):
        ctx = self.make_context(
            method='POST',
            data={'subject': 'RE: Hip Hopera'},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert msg.subject == 'Hip Hopera'

    def test_recipient(self):
        address = 'test-conference@osf.io'
        ctx = self.make_context(
            method='POST',
            data={'recipient': address},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert msg.recipient == address

    def test_text(self):
        text = 'welcome to my nuclear family'
        ctx = self.make_context(
            method='POST',
            data={'stripped-text': text},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert msg.text == text

    def test_sender_name(self):
        names = [
            (' Fred', 'Fred'),
            ('Me‰¨ü', 'Me‰¨ü'),
            ('fred@queen.com', 'fred@queen.com'),
            ('Fred <fred@queen.com>', 'Fred'),
            ('"Fred" <fred@queen.com>', 'Fred'),
        ]
        for name in names:
            with self.make_context(data={'from': name[0]}):
                msg = message.ConferenceMessage()
                assert msg.sender_name == name[1]

    def test_sender_email(self):
        emails = [
            ('fred@queen.com', 'fred@queen.com'),
            ('FRED@queen.com', 'fred@queen.com')
        ]
        for email in emails:
            with self.make_context(data={'from': email[0]}):
                msg = message.ConferenceMessage()
                assert msg.sender_email == email[1]

    def test_route_invalid_pattern(self):
        with self.make_context(data={'recipient': 'spam@osf.io'}):
            self.app.application.preprocess_request()
            msg = message.ConferenceMessage()
            with pytest.raises(message.ConferenceError):
                msg.route

    def test_route_invalid_test(self):
        recipient = '{}conf-talk@osf.io'.format('' if settings.DEV_MODE else 'stage-')
        with self.make_context(data={'recipient': recipient}):
            self.app.application.preprocess_request()
            msg = message.ConferenceMessage()
            with pytest.raises(message.ConferenceError):
                msg.route

    def test_route_valid_alternate(self):
        conf = ConferenceFactory(endpoint='chocolate', active=True)
        conf.name = 'Chocolate Conference'
        conf.field_names['submission2'] = 'data'
        conf.save()
        recipient = '{}chocolate-data@osf.io'.format('test-' if settings.DEV_MODE else '')
        with self.make_context(data={'recipient': recipient}):
            self.app.application.preprocess_request()
            msg = message.ConferenceMessage()
            assert msg.conference_name == 'chocolate'
            assert msg.conference_category == 'data'
        conf.__class__.delete(conf)

    def test_route_valid_b(self):
        recipient = '{}conf-poster@osf.io'.format('test-' if settings.DEV_MODE else '')
        with self.make_context(data={'recipient': recipient}):
            self.app.application.preprocess_request()
            msg = message.ConferenceMessage()
            assert msg.conference_name == 'conf'
            assert msg.conference_category == 'poster'

    def test_alternate_route_invalid(self):
        recipient = '{}chocolate-data@osf.io'.format('test-' if settings.DEV_MODE else '')
        with self.make_context(data={'recipient': recipient}):
            self.app.application.preprocess_request()
            msg = message.ConferenceMessage()
            with pytest.raises(message.ConferenceError):
                msg.route

    def test_attachments_count_zero(self):
        with self.make_context(data={'attachment-count': '0'}):
            msg = message.ConferenceMessage()
            assert msg.attachments == []

    def test_attachments_count_one(self):
        content = b'slightly mad'
        sio = BytesIO(content)
        ctx = self.make_context(
            method='POST',
            data={
                'attachment-count': 1,
                'attachment-1': (sio, 'attachment-1'),
            },
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert len(msg.attachments) == 1
            assert msg.attachments[0].read() == content


class TestConferenceEmailViews(OsfTestCase):

    def test_redirect_to_meetings_url(self):
        url = '/presentations/'
        res = self.app.get(url)
        assert res.status_code == 302
        res = self.app.get(url, follow_redirects=True)
        assert res.request.path == '/meetings/'

    def test_conference_submissions(self):
        AbstractNode.objects.all().delete()
        conference1 = ConferenceFactory()
        conference2 = ConferenceFactory()
        # Create conference nodes
        create_fake_conference_nodes(
            3,
            conference1,
        )
        create_fake_conference_nodes(
            2,
            conference2,
        )

        url = api_url_for('conference_submissions')
        res = self.app.get(url)
        assert res.json['success']

    def test_conference_plain_returns_200(self):
        conference = ConferenceFactory()
        url = web_url_for('conference_results__plain', meeting=conference.endpoint)
        res = self.app.get(url)
        assert res.status_code == 200

    def test_conference_data(self):
        conference = ConferenceFactory()

        # Create conference nodes
        n_conference_nodes = 3
        create_fake_conference_nodes(
            n_conference_nodes,
            conference,
        )
        # Create a non-conference node
        ProjectFactory()

        url = api_url_for('conference_data', meeting=conference.endpoint)
        res = self.app.get(url)
        assert res.status_code == 200
        assert len(res.json) == n_conference_nodes

    # Regression for OSF-8864 to confirm bad project data does not make whole conference break
    def test_conference_bad_data(self):
        conference = ConferenceFactory()

        # Create conference nodes
        n_conference_nodes = 3
        n_conference_nodes_bad = 1
        create_fake_conference_nodes_bad_data(
            conference,
            n_conference_nodes,
            n_conference_nodes_bad,
            conference,
        )
        # Create a non-conference node
        ProjectFactory()

        url = api_url_for('conference_data', meeting=conference.endpoint)
        res = self.app.get(url)
        assert res.status_code == 200
        assert len(res.json) == n_conference_nodes - n_conference_nodes_bad

    def test_conference_data_url_upper(self):
        conference = ConferenceFactory()

        # Create conference nodes
        n_conference_nodes = 3
        create_fake_conference_nodes(
            n_conference_nodes,
            conference,
        )
        # Create a non-conference node
        ProjectFactory()

        url = api_url_for('conference_data', meeting=conference.endpoint.upper())
        res = self.app.get(url)
        assert res.status_code == 200
        assert len(res.json) == n_conference_nodes

    def test_conference_data_tag_upper(self):
        conference = ConferenceFactory()

        # Create conference nodes
        n_conference_nodes = 3
        create_fake_conference_nodes(
            n_conference_nodes,
            conference,
        )
        # Create a non-conference node
        ProjectFactory()

        url = api_url_for('conference_data', meeting=conference.endpoint)
        res = self.app.get(url)
        assert res.status_code == 200
        assert len(res.json) == n_conference_nodes

    def test_conference_results(self):
        conference = ConferenceFactory()

        url = web_url_for('conference_results', meeting=conference.endpoint)
        res = self.app.get(url)
        assert res.status_code == 200

    def test_confererence_results_endpoint_is_case_insensitive(self):
        ConferenceFactory(endpoint='StudySwap')
        url = web_url_for('conference_results', meeting='studyswap')
        res = self.app.get(url)
        assert res.status_code == 200


class TestConferenceModel(OsfTestCase):

    def test_endpoint_is_required(self):
        with pytest.raises(IntegrityError):
            ConferenceFactory(endpoint=None, name=fake.company()).save()

    def test_name_is_required(self):
        with pytest.raises(IntegrityError):
            ConferenceFactory(endpoint='spsp2014', name=None).save()

    def test_default_field_names(self):
        conf = ConferenceFactory(endpoint='cookie', name='Cookies Conference')
        conf.save()
        assert conf.field_names['submission1'] == 'poster'
        assert conf.field_names['mail_subject'] == 'Presentation title'

    def test_conference_valid_submissions(self):
        conf = ConferenceFactory(endpoint='Hamburgers', name='Hamburger conference')
        conf.save()

        # 3 good nodes added
        create_fake_conference_nodes(3, conf)

        # Deleted node added
        deleted_node = ProjectFactory(is_public=True)
        deleted_node.is_deleted = True
        deleted_node.save()
        conf.submissions.add(deleted_node)

        # Private node added
        private_node = ProjectFactory(is_public=False)
        conf.submissions.add(private_node)

        assert conf.submissions.count() == 5
        assert conf.valid_submissions.count() == 3


class TestConferenceIntegration(ContextTestCase):

    @mock.patch('website.conferences.views.send_mail')
    @mock.patch('website.conferences.utils.upload_attachments')
    def test_integration(self, mock_upload, mock_send_mail):
        fullname = 'John Deacon'
        username = 'deacon@queen.com'
        title = 'good songs'
        conference = ConferenceFactory()
        body = 'dragon on my back'
        content = 'dragon attack'
        recipient = '{}{}-poster@osf.io'.format(
            'test-' if settings.DEV_MODE else '',
            conference.endpoint,
        )
        self.app.post(
            api_url_for('meeting_hook'),
            data={
                'X-Mailgun-Sscore': 0,
                'timestamp': '123',
                'token': 'secret',
                'signature': hmac.new(
                    key=settings.MAILGUN_API_KEY.encode(),
                    msg='{}{}'.format('123', 'secret').encode(),
                    digestmod=hashlib.sha256,
                ).hexdigest(),
                'attachment-count': '1',
                'X-Mailgun-Sscore': 0,
                'from': f'{fullname} <{username}>',
                'recipient': recipient,
                'subject': title,
                'stripped-text': body,
                'attachment-1': (BytesIO(content.encode()), 'attachment-1')
            },
        )
        assert mock_upload.called
        users = OSFUser.objects.filter(username=username)
        assert users.count() == 1
        nodes = AbstractNode.objects.filter(title=title)
        assert nodes.count() == 1
        node = nodes[0]
        assert WikiVersion.objects.get_for_node(node, 'home').content == body
        assert mock_send_mail.called
        call_args, call_kwargs = mock_send_mail.call_args
        assert_absolute(call_kwargs['conf_view_url'])
        assert_absolute(call_kwargs['set_password_url'])
        assert_absolute(call_kwargs['profile_url'])
        assert_absolute(call_kwargs['file_url'])
        assert_absolute(call_kwargs['node_url'])

    @mock.patch('website.conferences.views.send_mail')
    def test_integration_inactive(self, mock_send_mail):
        conference = ConferenceFactory(active=False)
        fullname = 'John Deacon'
        username = 'deacon@queen.com'
        title = 'good songs'
        body = 'dragon on my back'
        recipient = '{}{}-poster@osf.io'.format(
            'test-' if settings.DEV_MODE else '',
            conference.endpoint,
        )
        res = self.app.post(
            api_url_for('meeting_hook'),
            data={
                'X-Mailgun-Sscore': 0,
                'timestamp': '123',
                'token': 'secret',
                'signature': hmac.new(
                    key=settings.MAILGUN_API_KEY.encode(),
                    msg='{}{}'.format('123', 'secret').encode(),
                    digestmod=hashlib.sha256,
                ).hexdigest(),
                'attachment-count': '1',
                'X-Mailgun-Sscore': 0,
                'from': f'{fullname} <{username}>',
                'recipient': recipient,
                'subject': title,
                'stripped-text': body,
            },
        )
        assert res.status_code == 406
        call_args, call_kwargs = mock_send_mail.call_args
        assert call_args == (username, views.CONFERENCE_INACTIVE)
        assert call_kwargs['fullname'] == fullname
        assert_equal_urls(
            call_kwargs['presentations_url'],
            web_url_for('conference_view', _absolute=True),
        )

    @mock.patch('website.conferences.views.send_mail')
    @mock.patch('website.conferences.utils.upload_attachments')
    def test_integration_wo_full_name(self, mock_upload, mock_send_mail):
        username = 'no_full_name@mail.com'
        title = 'no full name only email'
        conference = ConferenceFactory()
        body = 'dragon on my back'
        content = 'dragon attack'
        recipient = '{}{}-poster@osf.io'.format(
            'test-' if settings.DEV_MODE else '',
            conference.endpoint,
        )
        self.app.post(
            api_url_for('meeting_hook'),
            data={
                'X-Mailgun-Sscore': 0,
                'timestamp': '123',
                'token': 'secret',
                'signature': hmac.new(
                    key=settings.MAILGUN_API_KEY.encode(),
                    msg='{}{}'.format('123', 'secret').encode(),
                    digestmod=hashlib.sha256,
                ).hexdigest(),
                'attachment-count': '1',
                'X-Mailgun-Sscore': 0,
                'from': username,
                'recipient': recipient,
                'subject': title,
                'stripped-text': body,
                'attachment-1': (BytesIO(content.encode()), 'attachment-1')
            },
        )
        assert mock_upload.called
        users = OSFUser.objects.filter(username=username)
        assert users.count() == 1
        nodes = AbstractNode.objects.filter(title=title)
        assert nodes.count() == 1
        node = nodes[0]
        assert WikiVersion.objects.get_for_node(node, 'home').content == body
        assert mock_send_mail.called
        call_args, call_kwargs = mock_send_mail.call_args
        assert_absolute(call_kwargs['conf_view_url'])
        assert_absolute(call_kwargs['set_password_url'])
        assert_absolute(call_kwargs['profile_url'])
        assert_absolute(call_kwargs['file_url'])
        assert_absolute(call_kwargs['node_url'])

    @mock.patch('website.conferences.views.send_mail')
    @mock.patch('website.conferences.utils.upload_attachments')
    def test_create_conference_node_with_same_name_as_existing_node(self, mock_upload, mock_send_mail):
        conference = ConferenceFactory()
        user = UserFactory()
        title = 'Long Live Greg'
        ProjectFactory(creator=user, title=title)

        body = 'Greg is a good plant'
        content = 'Long may they reign.'
        recipient = '{}{}-poster@osf.io'.format(
            'test-' if settings.DEV_MODE else '',
            conference.endpoint,
        )
        self.app.post(
            api_url_for('meeting_hook'),
            data={
                'X-Mailgun-Sscore': 0,
                'timestamp': '123',
                'token': 'secret',
                'signature': hmac.new(
                    key=settings.MAILGUN_API_KEY.encode(),
                    msg='{}{}'.format('123', 'secret').encode(),
                    digestmod=hashlib.sha256,
                ).hexdigest(),
                'attachment-count': '1',
                'X-Mailgun-Sscore': 0,
                'from': f'{user.fullname} <{user.username}>',
                'recipient': recipient,
                'subject': title,
                'stripped-text': body,
                'attachment-1':(BytesIO(content.encode()), 'attachment-1')
            },
        )

        assert AbstractNode.objects.filter(title=title, creator=user).count() == 2
        assert mock_upload.called
        assert mock_send_mail.called
