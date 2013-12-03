# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import unittest
from nose.tools import *  # PEP8 asserts

import pytz
import datetime
from dateutil import parser

from framework.auth import User
from framework.bcrypt import check_password_hash
from website.project.model import ApiKey, NodeFile, NodeLog

from tests.base import DbTestCase, Guid
from tests.factories import (UserFactory, ApiKeyFactory, NodeFactory,
    ProjectFactory, NodeLogFactory, WatchConfigFactory, MetaDataFactory,
    TagFactory, NodeWikiFactory)


GUID_FACTORIES = (UserFactory, TagFactory, NodeFactory, ProjectFactory,
                  MetaDataFactory)

class TestUser(DbTestCase):

    def setUp(self):
        self.user = UserFactory()

    def test_factory(self):
        # Clear users
        User.remove()
        user = UserFactory()
        assert_equal(User.find().count(), 1)
        assert_true(user.username)
        another_user = UserFactory(username="joe@example.com")
        assert_equal(another_user.username, "joe@example.com")
        assert_equal(User.find().count(), 2)
        assert_true(user.date_registered)

    def test_is_watching(self):
        # User watches a node
        watched_node = NodeFactory()
        unwatched_node = NodeFactory()
        config = WatchConfigFactory(node=watched_node)
        self.user.watched.append(config)
        self.user.save()
        assert_true(self.user.is_watching(watched_node))
        assert_false(self.user.is_watching(unwatched_node))

    def test_set_password(self):
        user = User(username="nick@cage.com", fullname="Nick Cage", is_registered=True)
        user.set_password("ghostrider")
        user.save()
        assert_true(check_password_hash(user.password, 'ghostrider'))

    def test_check_password(self):
        user = User(username="nick@cage.com", fullname="Nick Cage", is_registered=True)
        user.set_password("ghostrider")
        user.save()
        assert_true(user.check_password("ghostrider"))
        assert_false(user.check_password("ghostride"))


class TestMergingUsers(DbTestCase):

    def setUp(self):
        self.master = UserFactory(username="joe@example.com",
                            fullname="Joe Shmo",
                            is_registered=True,
                            emails=["joe@example.com"])
        self.dupe = UserFactory(username="joseph123@hotmail.com",
                            fullname="Joseph Shmo",
                            emails=["joseph123@hotmail.com"])

    def _merge_dupe(self):
        '''Do the actual merge.'''
        self.master.merge_user(self.dupe)
        self.master.save()

    def test_dupe_is_merged(self):
        self._merge_dupe()
        assert_true(self.dupe.is_merged)
        assert_equal(self.dupe.merged_by, self.master)

    def test_dupe_email_is_appended(self):
        self._merge_dupe()
        assert_in("joseph123@hotmail.com", self.master.emails)

    def test_inherits_projects_contributed_by_dupe(self):
        project = ProjectFactory()
        project.contributors.append(self.dupe)
        project.save()
        self._merge_dupe()
        assert_true(project.is_contributor(self.master))
        assert_false(project.is_contributor(self.dupe))

    def test_inherits_projects_created_by_dupe(self):
        project = ProjectFactory(creator=self.dupe)
        self._merge_dupe()
        assert_equal(project.creator, self.master)

    def test_adding_merged_user_as_contributor_adds_master(self):
        project = ProjectFactory(creator=UserFactory())
        self._merge_dupe()
        project.add_contributor(contributor=self.dupe)
        assert_true(project.is_contributor(self.master))
        assert_false(project.is_contributor(self.dupe))


class TestGUID(DbTestCase):

    def setUp(self):

        self.records = {}
        for factory in GUID_FACTORIES:
            record = factory()
            record.save()
            self.records[record._name] = record

    def test_guid(self):

        for record in self.records.values():

            record_guid = Guid.load(record._primary_key)

            # GUID must exist
            assert_false(record_guid is None)

            # Primary keys of GUID and record must be the same
            assert_equal(
                record_guid._primary_key,
                record._primary_key
            )

            # GUID must refer to record
            assert_equal(
                record_guid.referent,
                record
            )


class TestMetaData(DbTestCase):

    def setUp(self):
        pass

    def test_referent(self):
        pass

class TestNodeFile(DbTestCase):

    def setUp(self):
        self.node = ProjectFactory()
        self.node_file = NodeFile(node=self.node, path="foo.py", filename="foo.py", size=128)
        self.node.files_versions[self.node_file.clean_filename] = [self.node_file._primary_key]
        self.node.save()

    def test_url(self):
        assert_equal(self.node_file.api_url,
            "{0}files/{1}/".format(self.node.api_url, self.node_file.filename))

    def test_clean(self):
        assert_equal(self.node_file.clean_filename, "foo_py")

    def test_latest_version_number(self):
        assert_equal(self.node_file.latest_version_number, 1)

    def test_download_url(self):
        assert_equal(self.node_file.download_url,
            self.node.api_url + "files/download/{0}/version/1/".format(self.node_file.filename))


class TestApiKey(DbTestCase):

    def test_factory(self):
        key = ApiKeyFactory()
        user = UserFactory()
        user.api_keys.append(key)
        user.save()
        assert_equal(len(user.api_keys), 1)
        assert_equal(ApiKey.find().count(), 1)


class TestNodeWikiPage(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.wiki = NodeWikiFactory(user=self.user, node=self.project)

    def test_factory(self):
        wiki = NodeWikiFactory()
        assert_true(wiki.page_name)
        assert_true(wiki.version)
        assert_true(hasattr(wiki, "is_current"))
        assert_true(hasattr(wiki, "content"))
        assert_true(wiki.user)
        assert_true(wiki.node)

    def test_url(self):
        assert_equal(self.wiki.url, "{project_url}wiki/home/"
                                    .format(project_url=self.project.url))


class TestNode(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.parent = ProjectFactory()
        self.node = NodeFactory.build(creator=self.user)
        self.node.contributors.append(self.user)
        self.node.save()
        self.parent.nodes.append(self.node)
        self.parent.save()

    def test_node_factory(self):
        node = NodeFactory()
        assert_false(node.is_public)

    def test_watching(self):
        # A user watched a node
        user = UserFactory()
        config1 = WatchConfigFactory(node=self.node)
        user.watched.append(config1)
        user.save()
        assert_in(config1._id, self.node.watchconfig__watched)

    def test_url(self):
        url = self.node.url
        assert_equal(url, "/project/{0}/node/{1}/".format(self.parent._primary_key,
                                                        self.node._primary_key))

    def test_watch_url(self):
        url = self.node.watch_url
        assert_equal(url, "/api/v1/project/{0}/node/{1}/watch/"
                                .format(self.parent._primary_key,
                                        self.node._primary_key))

    def test_update_node_wiki(self):
        # user updates the wiki
        self.node.update_node_wiki("home", "Hello world", self.user, api_key=None)
        versions = self.node.wiki_pages_versions
        assert_equal(len(versions['home']), 1)
        # Makes another update
        self.node.update_node_wiki('home', "Hola mundo", self.user, api_key=None)
        # Now there are 2 versions
        assert_equal(len(versions['home']), 2)
        # A log event was saved
        assert_equal(self.node.logs[-1].action, "wiki_updated")

    def test_parent(self):
        assert_equal(self.node.parent, self.parent)

    def test_no_parent(self):
        node = NodeFactory()
        assert_equal(node.parent, None)

    def test_add_file(self):
        pass

    def _cmp_fork_original(self, fork_user, fork_date, fork, original,
                           title_prepend='Fork of '):
        """Compare forked node with original node. Verify copied fields,
        modified fields, and files; recursively compare child nodes.

        :param fork_user: User who forked the original nodes
        :param fork_date: Datetime (UTC) at which the original node was forked
        :param fork: Forked node
        :param original: Original node
        :param title_prepend: String prepended to fork title

        """
        # Test copied fields
        assert_equal(title_prepend + original.title, fork.title)
        assert_equal(original.category, fork.category)
        assert_equal(original.description, fork.description)
        assert_equal(original.logs, fork.logs[:-1])
        assert_true(len(fork.logs) == len(original.logs) + 1)
        assert_equal(fork.logs[-1].action, NodeLog.NODE_FORKED)
        assert_equal(original.tags, fork.tags)

        # Test modified fields
        # Note: Must cast ForeignList to list for comparison
        assert_equal(list(fork.contributors), [fork_user])
        assert_true((fork_date - fork.date_created) < datetime.timedelta(seconds=2))

        # Test that files were copied correctly
        for fname in original.files_versions:
            assert_true(fname in original.files_versions)
            assert_true(fname in fork.files_versions)
            assert_equal(
                len(original.files_versions[fname]),
                len(fork.files_versions[fname]),
             )
            for vidx in range(len(original.files_versions[fname])):
                file_original = NodeFile.load(original.files_versions[fname][vidx])
                file_fork = NodeFile.load(original.files_versions[fname][vidx])
                data_original = original.get_file(file_original.path, vidx)
                data_fork = fork.get_file(file_fork.path, vidx)
                assert_equal(data_original, data_fork)

        # Recursively compare children
        for idx, child in enumerate(original.nodes):
            if child.can_view(fork_user):
                self._cmp_fork_original(fork_user, fork_date, fork.nodes[idx],
                                        child, title_prepend='')

    def test_fork(self):
        """Omnibus test for forking.

        """
        # Add user as contributor
        self.parent.add_contributor(self.user, self.parent.creator)

        # Add file to test copying
        self.parent.add_file(self.user, None, 'test.txt', 'test content', 4,
                             'text/plain')
        self.node.add_file(self.user, None, 'test2.txt', 'test content2', 4,
                             'text/plain')
        self.node.add_file(self.user, None, 'test3.txt', 'test content3', 4,
                             'text/plain')

        # Log time
        fork_date = datetime.datetime.utcnow()

        # Fork node
        fork = self.parent.fork_node(user=self.user)

        # Compare fork to original
        self._cmp_fork_original(self.user, fork_date, fork, self.parent)

    def test_register(self):
        pass


class TestProject(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user, description='foobar')

    def test_project_factory(self):
        node = ProjectFactory()
        assert_equal(node.category, 'project')
        assert_equal(node.logs[-1].action, 'project_created')

    def test_url(self):
        url = self.project.url
        assert_equal(url, "/project/{0}/".format(self.project._primary_key))

    def test_api_url(self):
        api_url = self.project.api_url
        assert_equal(api_url, "/api/v1/project/{0}/".format(self.project._primary_key))

    def test_watch_url(self):
        watch_url = self.project.watch_url
        assert_equal(watch_url, "/api/v1/project/{0}/watch/".format(self.project._primary_key))

    def test_add_contributor(self):
        # A user is added as a contributor
        user2 = UserFactory()
        self.project.add_contributor(contributor=user2, user=self.user)
        self.project.save()
        assert_in(user2, self.project.contributors)
        assert_equal(self.project.logs[-1].action, 'contributor_added')

    def test_add_nonregistered_contributor(self):
        self.project.add_nonregistered_contributor(email="foo@bar.com", name="Weezy F. Baby", user=self.user)
        self.project.save()
        # Contributor list include nonregistered contributor
        latest_contributor = self.project.contributor_list[-1]
        assert_dict_equal(latest_contributor,
                        {"nr_name": "Weezy F. Baby", "nr_email": "foo@bar.com"})
        # A log event was added
        assert_equal(self.project.logs[-1].action, "contributor_added")

    def test_remove_contributor(self):
        # A user is added as a contributor
        user2 = UserFactory()
        self.project.add_contributor(contributor=user2, user=self.user)
        self.project.save()
        # The user is removed
        self.project.remove_contributor(user=self.user, contributor=user2, api_key=None)
        assert_not_in(user2, self.project.contributors)

    def test_set_title(self):
        proj = ProjectFactory(title="That Was Then", creator=self.user)
        proj.set_title("This is now", user=self.user)
        proj.save()
        # Title was changed
        assert_equal(proj.title, "This is now")
        # A log event was saved
        latest_log = proj.logs[-1]
        assert_equal(latest_log.action, "edit_title")
        assert_equal(latest_log.params['title_original'], "That Was Then")

    def test_contributor_can_edit(self):
        contributor = UserFactory()
        self.project.add_contributor(contributor=contributor, user=self.user)
        self.project.save()
        assert_true(self.project.can_edit(contributor))

    def test_creator_can_edit(self):
        assert_true(self.project.can_edit(self.user))

    def test_is_contributor(self):
        contributor = UserFactory()
        other_guy = UserFactory()
        self.project.add_contributor(contributor=contributor, user=self.user)
        self.project.save()
        assert_true(self.project.is_contributor(contributor))
        assert_false(self.project.is_contributor(other_guy))
        assert_false(self.project.is_contributor(None))

    def test_creator_is_contributor(self):
        assert_true(self.project.is_contributor(self.user))

    def test_cant_add_same_contributor_twice(self):
        contrib = UserFactory()
        self.project.add_contributor(contributor=contrib)
        self.project.save()
        self.project.add_contributor(contributor=contrib)
        self.project.save()
        assert_equal(len(self.project.contributors), 1)

    def test_add_contributors(self):
        user1 = UserFactory()
        user2 = UserFactory()
        self.project.add_contributors([user1, user2], user=self.user)
        self.project.save()
        assert_equal(len(self.project.contributors), 2)
        assert_equal(len(self.project.contributor_list), 2)
        assert_equal(self.project.logs[-1].params['contributors'],
                        [user1._id, user2._id])

    def test_set_permissions(self):
        self.project.set_permissions('public', user=self.user)
        self.project.save()
        assert_true(self.project.is_public)
        assert_equal(self.project.logs[-1].action, 'made_public')
        self.project.set_permissions('private', user=self.user)
        self.project.save()
        assert_false(self.project.is_public)
        assert_equal(self.project.logs[-1].action, NodeLog.MADE_PRIVATE)

    def test_set_description(self):
        old_desc = self.project.description
        self.project.set_description("new description", user=self.user)
        self.project.save()
        assert_equal(self.project.description, 'new description')
        latest_log = self.project.logs[-1]
        assert_equal(latest_log.action, NodeLog.EDITED_DESCRIPTION)
        assert_equal(latest_log.params['description_original'], old_desc)
        assert_equal(latest_log.params['description_new'], 'new description')

class TestNodeLog(DbTestCase):

    def setUp(self):
        self.log = NodeLogFactory()

    def test_node_log_factory(self):
        log = NodeLogFactory()
        assert_true(log.action)

    def test_tz_date(self):
        assert_equal(self.log.tz_date.tzinfo, pytz.UTC)

    def test_formatted_date(self):
        iso_formatted = self.log.formatted_date  # The string version in iso format
        # Reparse the date
        parsed = parser.parse(iso_formatted)
        assert_equal(parsed, self.log.tz_date)

    def test_serialized_user_url(self):
        data = self.log.serialize()
        assert_equal(data['user_url'], self.log.user.url)



class TestWatchConfig(DbTestCase):

    def tearDown(self):
        User.remove()

    def test_factory(self):
        config = WatchConfigFactory(digest=True, immediate=False)
        assert_true(config.digest)
        assert_false(config.immediate)
        assert_true(config.node._id)

if __name__ == '__main__':
    unittest.main()
