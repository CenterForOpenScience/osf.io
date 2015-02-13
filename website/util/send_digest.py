"""Script for sending OSF email digests to subscribed users and removing the records once sent."""

import datetime
import urlparse
import mock
import unittest
from bson.code import Code
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from framework import sentry
from framework.auth.core import User
from framework.mongo import database as db
from framework.tasks import app
from framework.tasks.handlers import queued_task
from website import mails, settings
from website.app import init_app
from website.util import web_url_for
from website.notifications.model import DigestNotification
from website.notifications.utils import NotificationsDict
from tests.base import OsfTestCase
from tests.factories import DigestNotificationFactory, UserFactory, ProjectFactory
import nose.tools


def main():
    init_app(routes=False)
    grouped_digests = group_digest_notifications_by_user()
    print send_digest(grouped_digests)


@queued_task
@app.task
def send_digest(grouped_digests):
    for group in grouped_digests:
        try:
            user = User.load(group['user_id'])
        except NoResultsFound:
            sentry.log_exception()
            sentry.log_message("A user with this username does not exist.")
            user = None

        info = group['info']
        sorted_messages = group_messages(info)

        if user and sorted_messages:
            mails.send_mail(
                to_addr=user.username,
                mail=mails.DIGEST,
                name=user.fullname,
                message=sorted_messages,
                url=urlparse.urljoin(settings.DOMAIN, 'settings/notifications/')
            )

    db.digestnotification.remove({'timestamp': {'$lt': datetime.datetime.utcnow(),
                                                '$gte': datetime.datetime.utcnow() - datetime.timedelta(hours=24)}})


def group_messages(notifications):
    d = NotificationsDict()
    for n in notifications:
        d.add_message(n['node_lineage'], n['message'])
    return d


def group_digest_notifications_by_user():
    return db['digestnotification'].group(
        key={'user_id': 1},
        condition={'timestamp': {'$lt': datetime.datetime.utcnow(),
                                 '$gte': datetime.datetime.utcnow() - datetime.timedelta(hours=24)}},
        initial={'info': []},
        reduce=Code("""function(curr, result) {
                            info = {
                                'message': {
                                    'message': curr.message,
                                    'timestamp': curr.timestamp
                                },
                                'node_lineage': curr.node_lineage
                            }
                            result.info.push(info);
                    };
                    """))


class TestSendDigest(OsfTestCase):
    def test_group_digest_notifications_by_user(self):
        user = UserFactory()
        user2 = UserFactory()
        project = ProjectFactory()
        timestamp = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).replace(microsecond=0)
        d = DigestNotificationFactory(
            user_id=user._id,
            timestamp=timestamp,
            message='Hello',
            node_lineage=[project._id]
        )
        d.save()
        d2 = DigestNotificationFactory(
            user_id=user2._id,
            timestamp=timestamp,
            message='Hello',
            node_lineage=[project._id]
        )
        d2.save()
        user_groups = group_digest_notifications_by_user()
        info = [{
                u'message': {
                    u'message': u'Hello',
                    u'timestamp': timestamp,
                },
                u'node_lineage': [unicode(project._id)]
                }]
        expected = [{
                    u'user_id': user._id,
                    u'info': info
                    },
                    {
                    u'user_id': user2._id,
                    u'info': info
                    }]
        nose.tools.assert_equal(len(user_groups), 2)
        nose.tools.assert_equal(user_groups, expected)

    @unittest.skipIf(settings.USE_CELERY, 'Digest emails must be sent synchronously for this test')
    @mock.patch('website.mails.send_mail')
    def test_send_digest_called_with_correct_args(self, mock_send_mail):
        d = DigestNotificationFactory(
            user_id=UserFactory()._id,
            timestamp=datetime.datetime.utcnow(),
            message='Hello',
            node_lineage=[ProjectFactory()._id]
        )
        d.save()
        user_groups = group_digest_notifications_by_user()
        send_digest(user_groups)
        nose.tools.assert_true(mock_send_mail.called)

        user = User.load(user_groups[2]['user_id'])
        mock_send_mail.assert_called_with(
            to_addr=user.username,
            mail=mails.DIGEST,
            name=user.fullname,
            message=group_messages(user_groups[2]['info']),
            url=urlparse.urljoin(settings.DOMAIN, web_url_for('user_notifications'))
        )

    @unittest.skipIf(settings.USE_CELERY, 'Digest emails must be sent synchronously for this test')
    def test_send_digest_deletes_sent_digest_notifications(self):
        d = DigestNotificationFactory(
            user_id=UserFactory()._id,
            timestamp=datetime.datetime.utcnow(),
            message='Hello',
            node_lineage=[ProjectFactory()._id]
        )
        id = d._id
        user_groups = group_digest_notifications_by_user()
        send_digest(user_groups)
        with nose.tools.assert_raises(NoResultsFound):
            DigestNotification.find_one(Q('_id', 'eq', id))


if __name__ == '__main__':
    main()