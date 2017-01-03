import time
from datetime import datetime
import unittest
import random

from tests.base import DbTestCase
from tests.factories import UserFactory

from framework.discourse import common, projects, topics, users

# http://stackoverflow.com/questions/3335268/are-object-literals-pythonic
class literal(object):
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
    def __repr__(self):
        return 'literal(%s)' % ', '.join('%s = %r' % i for i in sorted(self.__dict__.iteritems()))
    def __str__(self):
        return repr(self)

alreadyUsedRandomGuids = []
def randomGuid():
    newGuid = str(random.randint(0, 99999))
    while newGuid in alreadyUsedRandomGuids:
        newGuid = str(random.randint(0, 99999))
    alreadyUsedRandomGuids.append(newGuid)
    return newGuid

class TestDiscourse(DbTestCase):
    def setUp(self):
        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.user2.discourse_user_created = False
        self.project_node = literal(label='The Test Project', _id='testproject' + randomGuid(),
                               contributors=[self.user1], is_public=False, is_deleted=False,
                               discourse_project_created=False, discourse_topic_id=None,
                               discourse_project_public=False, discourse_project_users=None,
                               discourse_topic_title=None, discourse_topic_parent_guids=None,
                               discourse_project_deleted=False, discourse_topic_deleted=False,
                               discourse_post_id=None, category='Project',
                               description=None, license=None,
                               private_links_active=[], discourse_view_only_keys=None,
                               parent_node=None, date_created=datetime.today())
        self.project_node.target_type = 'nodes'
        self.project_node.guid_id = self.project_node._id
        self.project_node.save = lambda *args: None

        self.component_node = literal(label='The Test Analysis', _id='testanalysis' + randomGuid(),
                               contributors=[self.user1], is_public=False, is_deleted=False,
                               discourse_project_created=False, discourse_topic_id=None,
                               discourse_project_public=False, discourse_project_users=None,
                               discourse_topic_title=None, discourse_topic_parent_guids=None,
                               discourse_project_deleted=False, discourse_topic_deleted=False,
                               discourse_post_id=None, category='Analysis',
                               description=None, license=None,
                               private_links_active=[], discourse_view_only_keys=None,
                               parent_node=self.project_node, date_created=datetime.today())
        self.component_node.target_type = 'nodes'
        self.component_node.guid_id = self.component_node._id
        self.component_node.save = lambda *args: None

        self.file_node = literal(_id='testfile' + randomGuid(), label='superRickyRobot.jpg', node=self.project_node,
                                is_deleted=False,
                                discourse_topic_id=None, discourse_post_id=None,
                                discourse_topic_title=None, discourse_topic_parent_guids=None,
                                discourse_topic_deleted=False,
                                date_created=datetime.today())
        self.file_node.target_type = 'files'
        self.file_node.guid_id = 'a' + randomGuid()
        self.file_node.save = lambda *args: None

    def tearDown(self):
        topics.delete_topic(self.project_node)
        topics.delete_topic(self.component_node)
        topics.delete_topic(self.file_node)
        time.sleep(0.125)
        projects.delete_project(self.component_node)
        projects.delete_project(self.project_node)
        time.sleep(0.125)
        users.delete_user(self.user1)
        users.delete_user(self.user2)

    def test_contributors(self):
        """ The contributors of a project should persist.
        """
        self.project_node.contributors = [self.user1, self.user2]
        projects.sync_project(self.project_node)
        self.assertEquals(len(projects.get_project(self.project_node)['contributors']), 2)
        time.sleep(0.125)

        self.project_node.contributors = [self.user1]
        projects.sync_project(self.project_node)
        self.assertEquals(len(projects.get_project(self.project_node)['contributors']), 1)
        time.sleep(0.125)

        self.project_node.contributors = []
        projects.sync_project(self.project_node)
        self.assertEquals(len(projects.get_project(self.project_node)['contributors']), 0)
        time.sleep(0.125)

    def test_project_publicity(self):
        """ A private project should be visible only to the contributors
        """
        self.project_node.is_public = False
        self.project_node.contributors = [self.user1]

        projects.sync_project(self.project_node)
        projects.get_project(self.project_node, user=self.user1)

        with self.assertRaises(common.DiscourseException):
            projects.get_project(self.project_node, user=self.user2)

        self.project_node.is_public = True
        projects.sync_project(self.project_node)
        projects.get_project(self.project_node, user=self.user2)

    def test_project_viewonly(self):
        """ A private project should be visible to anyone with a view_only link
        """
        self.project_node.is_public = False
        self.project_node.private_links_active = [literal(key='abcdefghijk', anonymous=False)]
        self.project_node.contributors = [self.user1]

        projects.sync_project(self.project_node)
        projects.get_project(self.project_node, user=self.user2, view_only='abcdefghijk')

        with self.assertRaises(common.DiscourseException):
            projects.get_project(self.project_node, user=self.user2, view_only='abc')

    def test_topic_custom_fields(self):
        """ custom information set in the project and topic should persist when the topic is returned
        """
        self.project_node.is_public = True

        topics.sync_topic(self.project_node)
        topic_json = topics.get_topic(self.project_node)
        self.assertEquals(topic_json['topic_guid'], self.project_node._id)
        self.assertEquals(topic_json['slug'], self.project_node._id)
        self.assertEquals(topic_json['title'], self.project_node.label)
        self.assertEquals(topic_json['parent_guids'], [self.project_node._id])
        self.assertEquals(topic_json['parent_names'], [self.project_node.label])
        self.assertEquals(topic_json['project_is_public'], True)

        self.component_node.is_public = False
        topics.sync_topic(self.component_node)
        topics.topic_json = topics.get_topic(self.component_node)
        self.assertEquals(topic_json['topic_guid'], self.component_node._id)
        self.assertEquals(topic_json['slug'], self.component_node._id)
        self.assertEquals(topic_json['title'], self.component_node.label)
        self.assertEquals(topic_json['parent_guids'], [self.component_node._id, self.project_node._id])
        self.assertEquals(topic_json['parent_names'], [self.component_node.label, self.project_node.label])
        self.assertEquals(topic_json['project_is_public'], False)

        topic_json = topics.get_topic(self.project_node)
        self.assertEquals(topic_json['topic_guid'], self.project_node._id)

    def test_recover_lost_project(self):
        """ Asking Discourse to recreate an existing project should not cause errors.
        """
        projects.sync_project(self.project_node)
        self.project_node.discourse_project_created = False
        projects.sync_project(self.project_node)
        self.assertEquals(self.project_node.discourse_project_created, True)

    def test_multiple_sync_free(self):
        """ sync_project and sync_topic should cost nothing when there are no new changes to push to Discourse.
        """
        topics.sync_topic(self.project_node)

        start_time = time.time()
        projects.sync_project(self.project_node)
        sync_time = time.time() - start_time
        self.assertLess(sync_time, 0.01)

        self.project_node.contributors = [self.user1, self.user2]
        start_time = time.time()
        projects.sync_project(self.project_node)
        sync_time = time.time() - start_time
        self.assertGreater(sync_time, 0.01)

        start_time = time.time()
        projects.sync_project(self.project_node)
        sync_time = time.time() - start_time
        self.assertLess(sync_time, 0.01)

    def test_delete_topic(self):
        """ a topic can be deleted independant of a project
        """
        projects.sync_project(self.project_node)
        topics.delete_topic(self.project_node)

        with self.assertRaises(common.DiscourseException):
            topics.get_topic(self.project_node)

    def test_delete_undelete_project(self):
        """ a deleted project should be innacessible until it is undeleted
        """
        projects.sync_project(self.project_node)
        projects.sync_project(self.component_node)
        topics.sync_topic(self.file_node)

        projects.delete_project(self.project_node)

        with self.assertRaises(common.DiscourseException):
            projects.get_project(self.project_node)

        with self.assertRaises(common.DiscourseException):
            projects.get_topic(self.project_node)

        with self.assertRaises(common.DiscourseException):
            topics.get_topic(self.component_node)

        with self.assertRaises(common.DiscourseException):
            projects.get_topic(self.file_node)

        projects.undelete_project(self.project_node)

        projects.get_project(self.project_node)
        topics.get_topic(self.project_node)
        topics.get_topic(self.component_node)
        topics.get_topic(self.file_node)

if __name__ == '__main__':
    unittest.main()
