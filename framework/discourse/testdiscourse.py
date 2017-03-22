import time
import unittest
import random

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory, PrivateLinkFactory

from framework.auth import Auth
from framework.discourse import projects, topics, users
import website.files.models

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
        self.auth = Auth(user=self.user1)
        self.user2 = UserFactory()
        self.user2.discourse_user_created = False
        self.project_node = ProjectFactory(title='The Test Project', _id='testproject' + randomGuid(),
                               creator=self.user1, is_public=False, category='project')

        self.component_node = ProjectFactory(title='The Test Analysis', _id='testanalysis' + randomGuid(),
                               creator=self.user1, is_public=False, category='analysis',
                               parent=self.project_node)

        self.file_node = website.files.models.StoredFileNode(_id='testfile' + randomGuid(),
            name='superRickyRobot.jpg', node=self.project_node,
            path='testfolder', provider='test', materialized_path='/test/path/superRickyRobot.jpg')

    def tearDown(self):
        self.assertTrue(topics.delete_topic(self.file_node))
        self.assertTrue(topics.delete_topic(self.component_node))
        self.assertTrue(topics.delete_topic(self.project_node))
        time.sleep(0.125)
        self.assertTrue(projects.delete_project(self.component_node))
        self.assertTrue(projects.delete_project(self.project_node))
        time.sleep(0.125)
        self.assertTrue(users.delete_user(self.user1))
        self.assertTrue(users.delete_user(self.user2))

    def test_contributors(self):
        """ The contributors of a project should persist.
        """
        self.project_node.add_contributor(self.user2)
        self.assertTrue(projects.sync_project(self.project_node))
        self.assertEquals(len(projects.get_project(self.project_node)['contributors']), 2)
        time.sleep(0.125)

        self.project_node.remove_contributor(self.user2, auth=self.auth)
        self.assertTrue(projects.sync_project(self.project_node))
        self.assertEquals(len(projects.get_project(self.project_node)['contributors']), 1)
        time.sleep(0.125)

        self.project_node.remove_contributor(self.user1, auth=self.auth)
        self.assertTrue(projects.sync_project(self.project_node))
        self.assertEquals(len(projects.get_project(self.project_node)['contributors']), 0)
        time.sleep(0.125)

    def test_project_publicity(self):
        """ A private project should be visible only to the contributors
        """
        self.project_node.is_public = False

        self.assertTrue(projects.sync_project(self.project_node))
        self.assertIsNotNone(projects.get_project(self.project_node, user=self.user1))
        self.assertIsNone(projects.get_project(self.project_node, user=self.user2))

        self.project_node.is_public = True
        self.assertTrue(projects.sync_project(self.project_node))
        self.assertIsNotNone(projects.get_project(self.project_node, user=self.user2))

    def test_project_viewonly(self):
        """ A private project should be visible to anyone with a view_only link
        """
        priv_link = PrivateLinkFactory()
        priv_link.nodes.append(self.project_node)
        priv_link.save()

        self.project_node.is_public = False

        self.assertTrue(projects.sync_project(self.project_node))
        self.assertIsNotNone(projects.get_project(self.project_node, user=self.user2, view_only=priv_link.key))
        self.assertIsNone(projects.get_project(self.project_node, user=self.user2, view_only='abc'))

    def test_topic_custom_fields(self):
        """ custom information set in the project and topic should persist when the topic is returned
        """
        self.project_node.is_public = True

        self.assertTrue(projects.sync_project(self.project_node))
        topic_json = topics.get_topic(self.project_node)
        self.assertEquals(topic_json['topic_guid'], self.project_node._id)
        self.assertEquals(topic_json['slug'], self.project_node._id)
        self.assertEquals(topic_json['title'], self.project_node.label)
        self.assertEquals(topic_json['parent_guids'], [self.project_node._id])
        self.assertEquals(topic_json['parent_names'], [self.project_node.label])
        self.assertEquals(topic_json['project_is_public'], True)

        self.component_node.is_public = False
        self.assertTrue(projects.sync_project(self.component_node))
        topic_json = topics.get_topic(self.component_node)
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
        self.assertTrue(projects.sync_project(self.project_node))
        self.project_node.discourse_project_created = False
        self.assertTrue(projects.sync_project(self.project_node))
        self.assertTrue(self.project_node.discourse_project_created)

    def test_multiple_sync_free(self):
        """ sync_project and sync_topic should cost nothing when there are no new changes to push to Discourse.
        """
        self.assertTrue(topics.sync_topic(self.project_node))

        start_time = time.time()
        self.assertTrue(projects.sync_project(self.project_node))
        sync_time = time.time() - start_time
        self.assertLess(sync_time, 0.01)

        self.project_node.add_contributor(self.user2)
        start_time = time.time()
        self.assertTrue(projects.sync_project(self.project_node))
        sync_time = time.time() - start_time
        self.assertGreater(sync_time, 0.01)

        start_time = time.time()
        self.assertTrue(projects.sync_project(self.project_node))
        sync_time = time.time() - start_time
        self.assertLess(sync_time, 0.01)

    def test_delete_topic(self):
        """ a topic can be deleted independant of a project
        """
        self.assertTrue(projects.sync_project(self.project_node))
        self.assertTrue(topics.delete_topic(self.project_node))
        self.assertIsNone(topics.get_topic(self.project_node))

    def test_delete_undelete_project(self):
        """ a deleted project should be innacessible until it is undeleted
        """
        self.assertTrue(projects.sync_project(self.project_node))
        self.assertTrue(projects.sync_project(self.component_node))
        self.assertTrue(topics.sync_topic(self.file_node))

        self.assertTrue(projects.delete_project(self.project_node))

        self.assertIsNone(projects.get_project(self.project_node))
        self.assertIsNone(topics.get_topic(self.project_node))
        self.assertIsNone(topics.get_topic(self.component_node))
        self.assertIsNone(topics.get_topic(self.file_node))

        self.assertTrue(projects.undelete_project(self.project_node))

        self.assertIsNotNone(projects.get_project(self.project_node))
        self.assertIsNotNone(topics.get_topic(self.project_node))
        self.assertIsNotNone(topics.get_topic(self.component_node))
        self.assertIsNotNone(topics.get_topic(self.file_node))

if __name__ == '__main__':
    unittest.main()
