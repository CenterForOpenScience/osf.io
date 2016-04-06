from datetime import datetime
from framework.auth.core import User
from scripts.update_comments import update_comments_viewed_timestamp
from tests.base import OsfTestCase
from tests.factories import UserFactory
from nose.tools import *  # PEP8 asserts


class TestUpdateCommentFields(OsfTestCase):

    def tearDown(self):
        super(TestUpdateCommentFields, self).tearDown()
        User.remove()

    def test_update_comments_viewed_timestamp_none(self):
        user = UserFactory()
        user.comments_viewed_timestamp = {}
        user.save()
        update_comments_viewed_timestamp()
        user.reload()
        assert_equal(user.comments_viewed_timestamp, {})

    def test_update_comments_viewed_timestamp(self):
        user = UserFactory()
        timestamp = datetime.utcnow().replace(microsecond=0)
        user.comments_viewed_timestamp = {
            'node_id': {
                'node': timestamp,
                'files': {
                    'file_id_1': timestamp,
                    'file_id_2': timestamp,
                }
            }
        }
        user.save()
        update_comments_viewed_timestamp()
        user.reload()
        assert_equal(user.comments_viewed_timestamp, {'node_id': timestamp, 'file_id_1': timestamp, 'file_id_2': timestamp})
