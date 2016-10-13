from . import sync_project, create_group, sync_group, delete_group, get_group_user_info, create_topic, get_topic, get_topics, delete_topic, delete_user, create_comment, edit_comment, delete_comment, undelete_comment
import common

import time
from datetime import datetime
import unittest
import random

from tests.base import DbTestCase
from tests.factories import UserFactory

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
        common.log_requests = True

        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.user2.discourse_user_created = False
        self.project_node = literal(label='The Test Project', _id='test1234',
                               contributors=[self.user1], is_public=False,
                               discourse_group_id=None, discourse_topic_id=None,
                               discourse_group_public=False, discourse_group_users=None,
                               discourse_topic_title=None, discourse_topic_parent_guids=None,
                               discourse_post_id=None, category='Project',
                               description=None, license=None,
                               parent_node=None, date_created=datetime.today())
        self.project_node.target_type = 'nodes'
        self.project_node.guid_id = self.project_node._id
        self.project_node.save = lambda *args: None

        self.component_node = literal(label='The Test Analysis', _id='analysis1234',
                               contributors=[self.user1], is_public=False,
                               discourse_group_id=None, discourse_topic_id=None,
                               discourse_group_public=False, discourse_group_users=None,
                               discourse_topic_title=None, discourse_topic_parent_guids=None,
                               discourse_post_id=None, category='Analysis',
                               description=None, license=None,
                               parent_node=self.project_node, date_created=datetime.today())
        self.component_node.target_type = 'nodes'
        self.component_node.guid_id = self.component_node._id
        self.component_node.save = lambda *args: None

        self.file_node = literal(_id='573cb78e96f6d02370c991a9', label='superRickyRobot.jpg', node=self.project_node,
                                discourse_topic_id=None, discourse_post_id=None,
                                discourse_topic_title=None, discourse_topic_parent_guids=None,
                                date_created=datetime.today())
        self.file_node.target_type = 'files'
        self.file_node.guid_id = 'a' + str(random.randint(0, 99999))
        self.file_node.save = lambda *args: None

        self.saved_group_id = None

    def tearDown(self):
        if self.project_node.discourse_group_id != self.saved_group_id:
            newer_group_id = self.project_node.discourse_group_id
            self.project_node.discourse_group_id = self.saved_group_id
            delete_group(self.project_node)
            self.project_node.discourse_group_id = newer_group_id

        delete_group(self.project_node)
        delete_group(self.component_node)
        delete_topic(self.project_node)
        delete_topic(self.component_node)
        delete_topic(self.file_node)
        delete_user(self.user1)
        delete_user(self.user2)

    def test_groups(self):
        delete_group(self.project_node)
        time.sleep(0.125)

        self.project_node.contributors = [self.user1, self.user2]
        sync_group(self.project_node)
        self.assertEquals(len(get_group_user_info(self.project_node)), 2)
        time.sleep(0.125)

        self.project_node.contributors = [self.user1]
        sync_group(self.project_node)
        self.assertEquals(len(get_group_user_info(self.project_node)), 1)
        time.sleep(0.125)

        self.project_node.contributors = [self.user1, self.user2]
        sync_group(self.project_node)
        self.assertEquals(len(get_group_user_info(self.project_node)), 2)
        time.sleep(0.125)

        self.project_node.contributors = []
        sync_group(self.project_node)
        self.assertEquals(len(get_group_user_info(self.project_node)), 0)
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

    def test_custom_fields(self):
        self.project_node.is_public = True
        create_topic(self.project_node)
        topic_json = get_topic(self.project_node)
        self.assertEquals(topic_json['topic_guid'], self.project_node._id)
        self.assertEquals(topic_json['slug'], self.project_node._id)
        self.assertEquals(topic_json['title'], self.project_node.label)
        self.assertEquals(topic_json['parent_guids'], [self.project_node._id])
        self.assertEquals(topic_json['parent_names'], [self.project_node.label])
        self.assertEquals(topic_json['project_is_public'], True)

        self.component_node.is_public = False
        create_topic(self.component_node)
        topic_json = get_topic(self.component_node)
        self.assertEquals(topic_json['topic_guid'], self.component_node._id)
        self.assertEquals(topic_json['slug'], self.component_node._id)
        self.assertEquals(topic_json['title'], self.component_node.label)
        self.assertEquals(topic_json['parent_guids'], [self.component_node._id, self.project_node._id])
        self.assertEquals(topic_json['parent_names'], [self.component_node.label, self.project_node.label])
        self.assertEquals(topic_json['project_is_public'], False)

        topic_json = get_topics(self.project_node)
        self.assertEquals(topic_json['topic_guid'], self.project_node._id)

    def test_recover_lost_group(self):
        create_group(self.project_node)
        self.saved_group_id = self.project_node.discourse_group_id
        self.project_node.discourse_group_id = None
        create_group(self.project_node)
        self.assertEquals(self.project_node.discourse_group_id, self.saved_group_id)

    def test_multiple_sync_free(self):
        create_topic(self.project_node)

        start_time = time.time()
        sync_project(self.project_node)
        sync_time = time.time() - start_time
        self.assertLess(sync_time, 0.01)

        self.project_node.contributors = [self.user1, self.user2]
        start_time = time.time()
        sync_project(self.project_node)
        sync_time = time.time() - start_time
        self.assertGreater(sync_time, 0.01)

        start_time = time.time()
        sync_project(self.project_node)
        sync_time = time.time() - start_time
        self.assertLess(sync_time, 0.01)

if __name__ == '__main__':
    unittest.main()

def stress_test():
    # Create a very large number of projects, topics, and posts!
    # We won't get rid of them when we are done because we want to see how performance holds up long term!
    # Perhaps only create a certain number each pass of this test...
    roundnumber = random.randint(0, 99999)
    user1 = literal(_id='%duser1' % roundnumber, username='%duser1@osf.io' % roundnumber, fullname='%duser1' % roundnumber,
                    discourse_user_created=False)
    user1.display_full_name = lambda *args: user1.fullname
    user1.profile_image_url = lambda *args: ''
    user1.save = lambda *args: None
    user2 = literal(_id='%duser2' % roundnumber, username='%duser2@osf.io' % roundnumber, fullname='%duser2' % roundnumber,
                    discourse_user_created=False)
    user2.display_full_name = lambda *args: user2.fullname
    user2.profile_image_url = lambda *args: ''
    user2.save = lambda *args: None
    for i in range(0, 1):
        project_node = literal(label='The Stress Test Project: %d_%d' % (roundnumber, i), _id='stress%d_%d' % (roundnumber, i),
                               contributors=[user1, user2], is_public=True,
                               discourse_group_id=None, discourse_topic_id=None,
                               discourse_group_public=False, discourse_group_users=None,
                               discourse_topic_title=None, discourse_topic_parent_guids=None,
                               discourse_post_id=None, category='Project',
                               description=None, license=None,
                               parent_node=None, date_created=datetime.today())
        project_node.target_type = 'nodes'
        project_node.guid_id = project_node._id
        project_node.save = lambda *args: None

        create_topic(project_node)

        for j in range(0, 50):
            file_node = literal(_id='longstressfileid%d_%d' % (i, j), label='stressFile%d_%d' % (i, j), node=project_node,
                                    discourse_topic_id=None, discourse_post_id=None,
                                    discourse_topic_title=None, discourse_topic_parent_guids=None,
                                    date_created=datetime.today())
            file_node.target_type = 'files'
            file_node.guid_id = 'a%d_%d_%d' % (random.randint(0, 99999), i, j)
            file_node.save = lambda *args: None

            start_time = time.time()
            comment_rounds = 16 if j < 5 else 1
            for k in range(0, comment_rounds):
                create_comment(file_node, 'Comment from system. This is comment round #%d' % k)
                create_comment(file_node, 'Comment from user1. This is comment round #%d' % k, user1)
                create_comment(file_node, 'Comment from user2. This is comment round #%d' % k, user2)
            print('%d comments for post %d took %f seconds' % (comment_rounds * 3, j, time.time() - start_time))
