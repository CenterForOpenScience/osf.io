# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import unittest
from nose.tools import *  # PEP8 asserts

import pytz
from dateutil import parser

from framework.auth import User
from framework.bcrypt import check_password_hash
from website.project.model import ApiKey, NodeFile

from tests.base import DbTestCase, Guid
from tests.factories import (UserFactory, ApiKeyFactory, NodeFactory,
    ProjectFactory, NodeLogFactory, WatchConfigFactory, MetaDataFactory,
    TagFactory)


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

    def setUp(self):
        pass

    def test_factory(self):
        key = ApiKeyFactory()
        user = UserFactory()
        user.api_keys.append(key)
        user.save()
        assert_equal(len(user.api_keys), 1)
        assert_equal(ApiKey.find().count(), 1)


class TestNode(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.parent = ProjectFactory()
        self.node = NodeFactory.build(creator=self.user, project=self.parent)
        self.node.contributors.append(self.user)
        self.node.save()
        #self.parent.nodes.append(self.node)
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


class TestNodeWiki(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.parent = ProjectFactory()
        self.node = NodeFactory.build(creator=self.user, project=self.parent)
        self.node.contributors.append(self.user)
        self.node.save()
        #self.parent.nodes.append(self.node)
        self.parent.save()

    def test_new_wiki(self):
        # There is no default wiki
        assert_equal(self.node.get_wiki_page("home"), None)

    def test_update_node_wiki(self):
        # user updates the wiki
        self.node.update_node_wiki("home", "Hello world", self.user, api_key=None)
        versions = self.node.wiki_pages_versions
        # There is now one version, logged, with the correct content
        assert_equal(len(versions['home']), 1)
        assert_equal(self.node.logs[-1].action, "wiki_updated")
        assert_equal(self.node.get_wiki_page("home").content, "Hello world")

    def test_update_node_wiki_twice(self):
        # user updates the wiki twice
        self.node.update_node_wiki("home", "Hello world", self.user, api_key=None)
        self.node.update_node_wiki('home', "Hola mundo", self.user, api_key=None)
        versions = self.node.wiki_pages_versions
        # Now there are 2 versions
        assert_equal(len(versions['home']), 2)
        # There are 2 logs saved
        assert_equal(self.node.logs[-1].action, "wiki_updated")
        assert_equal(self.node.logs[-2].action, "wiki_updated")
        # The new version is current, the old version is not
        assert_true(self.node.get_wiki_page("home", 2).is_current)
        assert_false(self.node.get_wiki_page("home", 1).is_current)
        # Both versions have the expected content
        assert_equal(self.node.get_wiki_page("home", 2).content, "Hola mundo")
        assert_equal(self.node.get_wiki_page("home", 1).content, "Hello world")

    def test_update_two_node_wikis(self):
        # user updates the wiki
        self.node.update_node_wiki("home", "Hello world", self.user, api_key=None)
        versions = self.node.wiki_pages_versions
        # user updates a second wiki for the same node
        self.node.update_node_wiki("second", "Hola mundo", self.user, api_key=None)
        # each wiki only has one version
        assert_equal(len(versions['home']), 1)
        assert_equal(len(versions['second']), 1)
        # There are 2 logs saved
        assert_equal(self.node.logs[-1].action, "wiki_updated")
        assert_equal(self.node.logs[-2].action, "wiki_updated")
        # each wiki has the expected content
        assert_equal(self.node.get_wiki_page("home").content, "Hello world")
        assert_equal(self.node.get_wiki_page("second").content, "Hola mundo")


class TestProject(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)

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
        other_guy = UserFactory()
        self.project.add_contributor(contributor=contributor, user=self.user)
        self.project.save()
        assert_true(self.project.can_edit(contributor))
        assert_false(self.project.can_edit(other_guy))

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
        assert_in(self.user, self.project.contributors)

    def test_cant_add_creator_as_contributor(self):
        self.project.add_contributor(contributor=self.user)
        self.project.save()
        assert_equal(len(self.project.contributors), 1)

    def test_cant_add_same_contributor_twice(self):
        contrib = UserFactory()
        self.project.add_contributor(contributor=contrib)
        self.project.save()
        self.project.add_contributor(contributor=contrib)
        self.project.save()
        assert_equal(len(self.project.contributors), 2)

    def test_add_contributors(self):
        user1 = UserFactory()
        user2 = UserFactory()
        self.project.add_contributors([user1, user2], user=self.user)
        self.project.save()
        assert_equal(len(self.project.contributors), 3)
        assert_equal(len(self.project.contributor_list), 3)
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
        assert_equal(self.project.logs[-1].action, 'made_private')

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
