# -*- coding: utf-8 -*-

from nose.tools import *  # noqa (PEP8 asserts)
from modularodm.exceptions import ValidationError

import hmac
import hashlib
from cStringIO import StringIO

from website import settings
from website.conferences.views import _render_conference_node
from website.conferences.model import Conference
from website.conferences import utils, message
from website.util import api_url_for, web_url_for
from framework.auth.core import Auth

from tests.base import OsfTestCase, fake
from tests.factories import ModularOdmFactory, FakerAttribute, ProjectFactory, UserFactory


class ConferenceFactory(ModularOdmFactory):
    FACTORY_FOR = Conference

    endpoint = FakerAttribute('slug')
    name = FakerAttribute('catch_phrase')
    active = True


def create_fake_conference_nodes(n, endpoint):
    nodes = []
    for i in range(n):
        node = ProjectFactory(is_public=True)
        node.add_tag(endpoint, Auth(node.creator))
        node.save()
        nodes.append(node)
    return nodes


class TestConferenceUtils(OsfTestCase):

    def test_get_or_create_user_exists(self):
        user = UserFactory()
        fetched, created = utils.get_or_create_user(user.fullname, user.username, True)
        assert_false(created)
        assert_equal(user._id, fetched._id)
        assert_false('is_spam' in fetched.system_tags)

    def test_get_or_create_user_not_exists(self):
        fullname = 'Roger Taylor'
        username = 'roger@queen.com'
        fetched, created = utils.get_or_create_user(fullname, username, False)
        assert_true(created)
        assert_equal(fetched.fullname, fullname)
        assert_equal(fetched.username, username)
        assert_false('is_spam' in fetched.system_tags)

    def test_get_or_create_user_is_spam(self):
        fullname = 'John Deacon'
        username = 'deacon@queen.com'
        fetched, created = utils.get_or_create_user(fullname, username, True)
        assert_true(created)
        assert_equal(fetched.fullname, fullname)
        assert_equal(fetched.username, username)
        assert_true('is_spam' in fetched.system_tags)

    def test_get_or_create_node_exists(self):
        node = ProjectFactory()
        fetched, created = utils.get_or_create_node(node.title, node.creator)
        assert_false(created)
        assert_equal(node._id, fetched._id)

    def test_get_or_create_node_title_not_exists(self):
        title = 'Night at the Opera'
        creator = UserFactory()
        node = ProjectFactory(creator=creator)
        fetched, created = utils.get_or_create_node(title, creator)
        assert_true(created)
        assert_not_equal(node._id, fetched._id)

    def test_get_or_create_node_user_not_exists(self):
        title = 'Night at the Opera'
        creator = UserFactory()
        node = ProjectFactory(title=title)
        fetched, created = utils.get_or_create_node(title, creator)
        assert_true(created)
        assert_not_equal(node._id, fetched._id)


class TestMessage(OsfTestCase):

    def setUp(self):
        super(OsfTestCase, self).setUp()

    def test_context(self, method='POST', **kwargs):
        data = {
            'X-Mailgun-Sscore': 0,
            'timestamp': '123',
            'token': 'secret',
            'signature': hmac.new(
                key=settings.MAILGUN_API_KEY,
                msg='{}{}'.format('123', 'secret'),
                digestmod=hashlib.sha256,
            ).hexdigest(),
        }
        data.update(kwargs.pop('data', {}))
        return self.app.app.test_request_context(method=method, data=data, **kwargs)

    def test_verify_signature_valid(self):
        with self.test_context():
            message.ConferenceMessage()

    def test_verify_signature_invalid(self):
        with self.test_context(data={'signature': 'fake'}):
            self.app.app.preprocess_request()
            with assert_raises(message.ConferenceError):
                message.ConferenceMessage()

    def test_is_spam_false_missing_headers(self):
        ctx = self.test_context(
            method='POST',
            data={'X-Mailgun-Sscore': message.SSCORE_MAX_VALUE - 1},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert not msg.is_spam

    def test_is_spam_false_all_headers(self):
        ctx = self.test_context(
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
        ctx = self.test_context(
            method='POST',
            data={'X-Mailgun-Sscore': message.SSCORE_MAX_VALUE + 1},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert msg.is_spam

    def test_is_spam_true_dkim(self):
        ctx = self.test_context(
            method='POST',
            data={'X-Mailgun-Dkim-Check-Result': message.DKIM_PASS_VALUES[0][::-1]},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert msg.is_spam

    def test_is_spam_true_spf(self):
        ctx = self.test_context(
            method='POST',
            data={'X-Mailgun-Spf': message.SPF_PASS_VALUES[0][::-1]},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert msg.is_spam

    def test_subject(self):
        ctx = self.test_context(
            method='POST',
            data={'subject': 'RE: Hip Hopera'},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert_equal(msg.subject, 'Hip Hopera')

    def test_recipient(self):
        address = 'test-conference@osf.io'
        ctx = self.test_context(
            method='POST',
            data={'recipient': address},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert_equal(msg.recipient, address)

    def test_text(self):
        text = 'welcome to my nuclear family'
        ctx = self.test_context(
            method='POST',
            data={'stripped-text': text},
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert_equal(msg.text, text)

    def test_sender_name(self):
        names = [
            (' Fred', 'Fred'),
            (u'Me‰¨ü', u'Me‰¨ü'),
            (u'Fred <fred@queen.com>', u'Fred'),
            (u'"Fred" <fred@queen.com>', u'Fred'),
        ]
        for name in names:
            with self.test_context(data={'from': name[0]}):
                msg = message.ConferenceMessage()
                assert_equal(msg.sender_name, name[1])

    def test_route_invalid_pattern(self):
        with self.test_context(data={'recipient': 'spam@osf.io'}):
            self.app.app.preprocess_request()
            msg = message.ConferenceMessage()
            with assert_raises(message.ConferenceError):
                msg.route

    def test_route_invalid_test(self):
        recipient = '{0}-conf-talk@osf.io'.format('' if settings.DEV_MODE else 'test')
        with self.test_context(data={'recipient': recipient}):
            self.app.app.preprocess_request()
            msg = message.ConferenceMessage()
            with assert_raises(message.ConferenceError):
                msg.route

    def test_route_valid(self):
        recipient = '{0}-conf-talk@osf.io'.format('test' if settings.DEV_MODE else '')
        with self.test_context(data={'recipient': recipient}):
            self.app.app.preprocess_request()
            msg = message.ConferenceMessage()
            assert_equal(msg.conference_name, 'conf')
            assert_equal(msg.conference_category, 'talk')

    def test_attachments_count_zero(self):
        with self.test_context(data={'attachment-count': '0'}):
            msg = message.ConferenceMessage()
            assert_equal(msg.attachments, [])

    def test_attachments_count_one(self):
        content = 'slightly mad'
        sio = StringIO(content)
        ctx = self.test_context(
            method='POST',
            data={
                'attachment-count': 1,
                'attachment-1': (sio, 'attachment-1'),
            },
        )
        with ctx:
            msg = message.ConferenceMessage()
            assert_equal(len(msg.attachments), 1)
            assert_equal(msg.attachments[0].read(), content)


class TestConferenceEmailViews(OsfTestCase):

    def test_conference_data(self):
        conference = ConferenceFactory()

        # Create conference nodes
        n_conference_nodes = 3
        conf_nodes = create_fake_conference_nodes(n_conference_nodes,
            conference.endpoint)
        # Create a non-conference node
        ProjectFactory()

        url = api_url_for('conference_data', meeting=conference.endpoint)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        json = res.json
        assert_equal(len(json), n_conference_nodes)

    def test_conference_results(self):
        conference = ConferenceFactory()

        url = web_url_for('conference_results', meeting=conference.endpoint)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)


class TestConferenceModel(OsfTestCase):

    def test_endpoint_and_name_are_required(self):
        with assert_raises(ValidationError):
            ConferenceFactory(endpoint=None, name=fake.company()).save()
        with assert_raises(ValidationError):
            ConferenceFactory(endpoint='spsp2014', name=None).save()
