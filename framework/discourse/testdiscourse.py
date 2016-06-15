from . import *
import time
import unittest
import random

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory

import ipdb

# http://stackoverflow.com/questions/3335268/are-object-literals-pythonic
class literal(object):
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
    def __repr__(self):
        return 'literal(%s)' % ', '.join('%s = %r' % i for i in sorted(self.__dict__.iteritems()))
    def __str__(self):
        return repr(self)

class TestDiscourse(DbTestCase):

    def setUp(self):
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.user2.discourse_user_created = False
        self.project_node = literal(title='The Test Project', _id='test1234',
                               contributors=[self.user1, self.user2], is_public=False,
                               discourse_group_id=None, discourse_topic_id=None,
                               parent=None)
        self.project_node.save = lambda *args: None
        self.file_node = literal(_id='573cb78e96f6d02370c991a9', name='superRickyRobot.jpg', node=self.project_node,
                                discourse_topic_id=None)
        self.file_node.get_guid = lambda *args: literal(_id=str(random.randint(0, 99999)), referent=self.file_node)
        self.file_node.save = lambda *args: None

    def tearDown(self):
        delete_group(self.project_node)
        delete_topic(self.project_node)
        delete_topic(self.file_node)
        delete_user(self.user1)
        delete_user(self.user2)

    def test_groups(self):
        delete_group(self.project_node)
        time.sleep(0.125)

        sync_group(self.project_node)
        self.assertEquals(len(get_group_users(self.project_node)), 2)
        time.sleep(0.125)

        self.project_node.contributors = [self.user1]
        sync_group(self.project_node)
        self.assertEquals(len(get_group_users(self.project_node)), 1)
        time.sleep(0.125)

        self.project_node.contributors = [self.user1, self.user2]
        sync_group(self.project_node)
        self.assertEquals(len(get_group_users(self.project_node)), 2)
        time.sleep(0.125)

        self.project_node.contributors = []
        sync_group(self.project_node)
        self.assertEquals(len(get_group_users(self.project_node)), 0)
        time.sleep(0.125)

        delete_group(self.project_node)
        self.assertIs(self.project_node.discourse_group_id, None)

    def test_comments(self):
        comment = create_comment(self.file_node, 'I think your robot is the coolest little bugger ever!', self.user1)
        comment_id = comment['post']['id']
        edit_comment(comment_id, 'Actually, your robot is the coolest little bugger ever!')
        delete_comment(comment_id)
        undelete_comment(comment_id)
        delete_comment(comment_id)

    def test_convert_topic_privacy(self):
        self.project_node.is_public = False
        ipdb.set_trace()
        create_topic(self.project_node)
        topic_json = get_topic(self.project_node)
        self.assertEquals(topic_json['archetype'], 'private_message')
        self.assertEquals(topic_json['details']['allowed_groups'][0]['name'], self.project_node._id)
        self.assertEquals(topic_json['tags'], [self.project_node._id])

        self.project_node.is_public = True
        topic_json = update_topic(self.project_node)
        self.assertEquals(topic_json['archetype'], 'regular')
        self.assertEquals(topic_json['tags'], [self.project_node._id])

        self.project_node.is_public = False
        topic_json = update_topic(self.project_node)
        self.assertEquals(topic_json['archetype'], 'private_message')
        self.assertEquals(topic_json['details']['allowed_groups'][0]['name'], self.project_node._id)
        self.assertEquals(topic_json['tags'], [self.project_node._id])

if __name__ == '__main__':
    unittest.main()
