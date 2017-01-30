#!/usr/bin/env python
# encoding: utf-8

import logging
import datetime

from django.utils import timezone
from modularodm import Q

from framework.email.tasks import send_email

from website import mails
from website import models
from website import settings
from website.app import init_app

from scripts import utils as script_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


FROM_ADDR = 'OSF Support <support@osf.io>'
MESSAGE_NAME = 'permissions_change'
SECURITY_MESSAGE = mails.Mail(
    'security_permissions_change',
    subject='OSF Privacy Notice',
)


def send_security_message(user, label, mail):
    if label in user.security_messages:
        return
    # Pass mailer so that celery is not used
    # Email synchronously so that user is only saved after email has been sent
    mails.send_mail(
        user.username,
        mail,
        from_addr=FROM_ADDR,
        mailer=send_email,
        user=user,
        username=settings.MANDRILL_USERNAME,
        password=settings.MANDRILL_PASSWORD,
        mail_server=settings.MANDRILL_MAIL_SERVER,
    )
    user.security_messages[label] = timezone.now()
    user.save()


def get_targets():
    # Active users who have not received the email
    query = (
        Q('security_messages.{0}'.format(MESSAGE_NAME), 'exists', False) &
        Q('is_registered', 'eq', True) &
        Q('password', 'ne', None) &
        Q('is_merged', 'ne', True) &
        Q('is_disabled', 'ne', True) &
        Q('date_confirmed', 'ne', None)
    )
    return models.User.find(query)


def main(dry_run):
    users = get_targets()
    for user in users:
        logger.info('Sending message to user {0!r}'.format(user))
        if not dry_run:
            send_security_message(user, MESSAGE_NAME, SECURITY_MESSAGE)


if __name__ == '__main__':
    import sys
    script_utils.add_file_logger(logger, __file__)
    dry_run = 'dry' in sys.argv
    init_app(set_backends=True, routes=False)
    main(dry_run=dry_run)


import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import UserFactory


class TestSendSecurityMessage(OsfTestCase):

    def tearDown(self):
        super(TestSendSecurityMessage, self).tearDown()
        models.User.remove()

    def test_get_targets(self):
        users = [UserFactory() for _ in range(3)]
        users[0].security_messages[MESSAGE_NAME] = timezone.now()
        users[0].save()
        targets = get_targets()
        assert_equal(set(targets), set(users[1:]))

    @mock.patch('scripts.admin_permission_email.send_email')
    def test_send_mail(self, mock_send_mail):
        user = UserFactory()
        send_security_message(user, MESSAGE_NAME, SECURITY_MESSAGE)
        user.reload()
        assert_in(MESSAGE_NAME, user.security_messages)

    @mock.patch('scripts.admin_permission_email.send_email')
    def test_main(self, mock_send_mail):
        [UserFactory() for _ in range(3)]
        assert_equal(len(get_targets()), 3)
        main(dry_run=False)
        assert_true(mock_send_mail.called)
        assert_equal(len(get_targets()), 0)

    @mock.patch('scripts.admin_permission_email.send_email')
    def test_main_dry(self, mock_send_mail):
        [UserFactory() for _ in range(3)]
        assert_equal(len(get_targets()), 3)
        main(dry_run=True)
        assert_false(mock_send_mail.called)
        assert_equal(len(get_targets()), 3)
