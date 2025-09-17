import time
import pytest
from framework.auth import signing
from waffle.testutils import override_switch
from osf import features
from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory
)
from tests.base import (
    OsfTestCase,
)
from tests.utils import get_mailhog_messages, delete_mailhog_messages, assert_emails
from importlib import import_module

from django.conf import settings as django_conf_settings
import itsdangerous
from framework.auth.core import Auth
from addons.osfstorage.models import OsfStorageFile
from tests.utils import capture_notifications
from website import settings

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore

pytestmark = pytest.mark.django_db


class TestCreateWBLog(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.user_non_contrib = AuthUserFactory()
        self.auth_obj = Auth(user=self.user)
        self.node = NodeFactory(creator=self.user)
        self.file = OsfStorageFile.create(
            target=self.node,
            path='/testfile',
            _id='testfile',
            name='testfile',
            materialized_path='/testfile'
        )
        self.file.save()
        self.session = SessionStore()
        self.session['auth_user_id'] = self.user._id
        self.session.create()
        self.cookie = itsdangerous.Signer(settings.SECRET_KEY).sign(self.session.session_key)

        self.source_dest = {
            'source': {
                'nid': self.node._id,
                'resource': self.node._id,
                'provider': 'osfstorage',
                'kind': 'file',
                'path': '/68c416d5993abb955649e39b',
                'name': 'file.png',
                'materialized': '/file.png',
                'extra': {}
            },
            'destination': {
                'nid': self.node._id,
                'resource': self.node._id,
                'extra': {
                    'guid': None,
                    'version': 1,
                    'downloads': 0,
                    'checkout': None,
                    'latestVersionSeen': None,
                    'hashes': {
                        'md5': '4df1cc7556a50f437318bed256795b99',
                        'sha256': 'd22324aa85762f3eeec36987b99a4e23067b492d8296ef246bb5d3eac0c21842'
                    }
                },
                'kind': 'file',
                'name': 'file.png',
                'path': '/68c416d5993abb955649e39b',
                'provider': 'osfstorage',
                'materialized': '/file.png',
                'etag': '568e49bea15354e35105a828a1775351921f2be70dedfcb3482d56f574189b6e',
                'contentType': None,
                'modified': '2025-09-12T12:49:25.352543+00:00',
                'modified_utc': '2025-09-12T12:49:25.352543+00:00',
                'created_utc': '2025-09-12T12:49:25.352543+00:00',
                'size': 208287,
                'sizeInt': 208287
            }
        }

    def build_payload(self, action, metadata, **kwargs):
        options = dict(
            auth={'id': self.user._id},
            action=action,
            provider='osfstorage',
            metadata=metadata,
            time=time.time() + 1000,
            **self.source_dest
        )
        options.update(kwargs)
        options = {
            key: value
            for key, value in options.items()
            if value is not None
        }
        message, signature = signing.default_signer.sign_payload(options)
        return {
            'payload': message,
            'signature': signature,
        }

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_log_move_file_error(self):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(action='move', metadata={'nid': self.node._id, 'materialized': path, 'kind': 'file', 'path': path}, errors=['some error'])
        delete_mailhog_messages()

        with capture_notifications(passthrough=True) as notifications:
            self.app.put(url, json=payload)

        mailhog = get_mailhog_messages()
        assert mailhog['count'] == len(notifications['emails'])
        assert_emails(mailhog, notifications)

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_log_copy_file_error(self):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(action='copy', metadata={'nid': self.node._id, 'materialized': path, 'kind': 'file', 'path': path}, errors=['some error'])
        delete_mailhog_messages()

        with capture_notifications(passthrough=True) as notifications:
            self.app.put(url, json=payload)
        mailhog = get_mailhog_messages()
        assert mailhog['count'] == len(notifications['emails'])
        assert_emails(mailhog, notifications)

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_log_move_file_success(self):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(action='move', metadata={'nid': self.node._id, 'materialized': path, 'kind': 'file', 'path': path})
        delete_mailhog_messages()

        with capture_notifications(passthrough=True) as notifications:
            self.app.put(url, json=payload)

        mailhog = get_mailhog_messages()
        assert mailhog['count'] == len(notifications['emails'])
        messages = {'count': mailhog['count'], 'items': mailhog['items'][::-1]}  # Reverse to get chronological order
        assert_emails(messages, notifications)

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_log_copy_file_success(self):
        path = 'pizza'
        url = self.node.api_url_for('create_waterbutler_log')
        payload = self.build_payload(action='copy', metadata={'nid': self.node._id, 'materialized': path, 'kind': 'file', 'path': path})
        delete_mailhog_messages()

        with capture_notifications(passthrough=True) as notifications:
            self.app.put(url, json=payload)

        mailhog = get_mailhog_messages()
        assert mailhog['count'] == len(notifications['emails'])
        messages = {'count': mailhog['count'], 'items': mailhog['items'][::-1]}  # Reverse to get chronological order
        assert_emails(messages, notifications)
