# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import unittest
from nose.tools import *  # PEP8 asserts

import pytz
import hashlib
import datetime
import urlparse
from dateutil import parser

from framework.analytics import get_total_activity_count
from framework.auth import User
from framework.auth.utils import parse_name
from framework import utils
from framework.bcrypt import check_password_hash
from framework.git.exceptions import FileNotModified
from website import settings, filters
from website.profile.utils import serialize_user
from website.project.model import ApiKey, NodeFile, NodeLog, ensure_schemas

from tests.base import DbTestCase, Guid
from tests.factories import (UserFactory, ApiKeyFactory, NodeFactory,
    ProjectFactory, NodeLogFactory, WatchConfigFactory, MetaDataFactory,
    NodeWikiFactory, UnregUserFactory, RegistrationFactory)


GUID_FACTORIES = UserFactory, NodeFactory, ProjectFactory, MetaDataFactory


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

    def test_format_surname(self):
        user = UserFactory(fullname='Duane Johnson')
        summary = user.get_summary(formatter='surname')
        assert_equal(
            summary['user_display_name'],
            'Johnson'
        )

    def test_format_surname_one_name(self):
        user = UserFactory(fullname='Rock')
        summary = user.get_summary(formatter='surname')
        assert_equal(
            summary['user_display_name'],
            'Rock'
        )

    def test_is_watching(self):
        # User watches a node
        watched_node = NodeFactory()
        unwatched_node = NodeFactory()
        config = WatchConfigFactory(node=watched_node)
        self.user.watched.append(config)
        self.user.save()
        assert_true(self.user.is_watching(watched_node))
        assert_false(self.user.is_watching(unwatched_node))

    def test_serialize(self):
        d = self.user.serialize()
        assert_equal(d['id'], str(self.user._primary_key))
        assert_equal(d['fullname'], self.user.fullname)
        assert_equal(d['registered'], self.user.is_registered)
        assert_equal(d['url'], self.user.url)

    def test_set_password(self):
        user = User(username="nick@cage.com", fullname="Nick Cage")
        user.set_password("ghostrider")
        user.save()
        assert_true(check_password_hash(user.password, 'ghostrider'))

    def test_check_password(self):
        user = User(username="nick@cage.com", fullname="Nick Cage")
        user.set_password("ghostrider")
        user.save()
        assert_true(user.check_password("ghostrider"))
        assert_false(user.check_password("ghostride"))

    def test_url(self):
        assert_equal(
            self.user.url,
            '/{0}/'.format(self.user._primary_key)
        )

    def test_absolute_url(self):
        assert_equal(
            self.user.absolute_url,
            urlparse.urljoin(settings.DOMAIN, '/{0}/'.format(self.user._primary_key))
        )

    def test_gravatar_url(self):
        expected = filters.gravatar(
            self.user,
            use_ssl=True,
            size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR
        )
        assert_equal(self.user.gravatar_url, expected)

    def test_activity_points(self):
        assert_equal(self.user.activity_points,
                    get_total_activity_count(self.user._primary_key))

    def test_serialize_user(self):
        master = UserFactory()
        user = UserFactory.build()
        master.merge_user(user, save=True)
        d = serialize_user(user)
        assert_equal(d['id'], user._primary_key)
        assert_equal(d['url'], user.url)
        assert_equal(d['username'], user.username)
        assert_equal(d['fullname'], user.fullname)
        assert_equal(d['registered'], user.is_registered)
        assert_equal(d['absolute_url'], user.absolute_url)
        assert_equal(d['date_registered'], user.date_registered.strftime("%Y-%m-%d"))

    def test_serialize_user_full(self):
        master = UserFactory()
        user = UserFactory.build()
        master.merge_user(user, save=True)
        d = serialize_user(user, full=True)
        assert_equal(d['id'], user._primary_key)
        assert_equal(d['url'], user.url)
        assert_equal(d['username'], user.username)
        assert_equal(d['fullname'], user.fullname)
        assert_equal(d['registered'], user.is_registered)
        assert_equal(d['gravatar_url'], user.gravatar_url)
        assert_equal(d['absolute_url'], user.absolute_url)
        assert_equal(d['date_registered'], user.date_registered.strftime("%Y-%m-%d"))
        assert_equal(d['activity_points'], user.activity_points)
        assert_equal(d['is_merged'], user.is_merged)
        assert_equal(d['merged_by']['url'], user.merged_by.url)
        assert_equal(d['merged_by']['absolute_url'], user.merged_by.absolute_url)
        projects = [
            node
            for node in user.node__contributed
            if node.category == 'project'
            and not node.is_registration
            and not node.is_deleted
        ]
        public_projects = [p for p in projects if p.is_public]
        assert_equal(d['number_projects'], len(projects))
        assert_equal(d['number_public_projects'], len(public_projects))

    def test_recently_added(self):
        # Project created
        project = ProjectFactory()

        assert_true(hasattr(self.user, "recently_added"))
        
        # Two users added as contributors
        user2 = UserFactory()
        user3 = UserFactory()
        project.add_contributor(contributor=user2, user=self.user)
        project.add_contributor(contributor=user3, user=self.user)
        assert_equal(user3, self.user.recently_added[0])
        assert_equal(user2, self.user.recently_added[1])
        assert_equal(len(self.user.recently_added), 2)

    def test_recently_added_multi_project(self):
        # Three users are created
        user2 = UserFactory()
        user3 = UserFactory()
        user4 = UserFactory()

        # 2 projects created
        project = ProjectFactory()
        project2 = ProjectFactory()

        # Users 2 and 3 are added to original project
        project.add_contributor(contributor=user2, user=self.user)
        project.add_contributor(contributor=user3, user=self.user)

        # Users 2 and 3 are added to original project
        project2.add_contributor(contributor=user2, user=self.user)
        project2.add_contributor(contributor=user4, user=self.user)

        assert_equal(user4, self.user.recently_added[0])
        assert_equal(user2, self.user.recently_added[1])
        assert_equal(user3, self.user.recently_added[2])
        assert_equal(len(self.user.recently_added), 3)

    def test_recently_added_length(self):
        # Project created
        project = ProjectFactory()

        assert_equal(len(self.user.recently_added), 0)
        # Add 17 users
        for _ in range(17):
            project.add_contributor(contributor=UserFactory(), user=self.user)

        assert_equal(len(self.user.recently_added), 15)



class TestUserParse(unittest.TestCase):

    def test_parse_first_last(self):
        parsed = parse_name('John Darnielle')
        assert_equal(parsed['given_name'], 'John')
        assert_equal(parsed['family_name'], 'Darnielle')

    def test_parse_first_last_particles(self):
        parsed = parse_name('John van der Slice')
        assert_equal(parsed['given_name'], 'John')
        assert_equal(parsed['family_name'], 'van der Slice')


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
        # Create a project with a NodeFile
        self.node = ProjectFactory()
        self.node_file = NodeFile(node=self.node, path="foo.py", filename="foo.py", size=128)
        self.node.files_versions[self.node_file.clean_filename] = [self.node_file._primary_key]
        self.node.save()

    def test_url(self):
        assert_equal(
            self.node_file.api_url,
            "{0}files/{1}/".format(self.node.api_url, self.node_file.filename),
        )

    def test_clean(self):
        assert_equal(self.node_file.clean_filename, "foo_py")

    def test_latest_version_number(self):
        assert_equal(self.node_file.latest_version_number, 1)

    def test_download_url(self):
        assert_equal(self.node_file.download_url,
            self.node.api_url + "files/download/{0}/version/1/".format(self.node_file.filename))


class TestAddFile(DbTestCase):

    def setUp(self):
        # Create a project
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        # Add a file
        self.file_name = "foo.py"
        self.file_key = self.file_name.replace(".", "_")
        self.node_file = self.project.add_file(
            self.user, None, self.file_name, "Content", 128, "Type"
        )
        self.project.save()

    def test_added(self):
        assert_equal(len(self.project.files_versions), 1)

    def test_component_add_file(self):
        # Add exact copy of parent project's file to component
        component = NodeFactory(project=self.project, creator=self.user)
        component_file = component.add_file(
            self.user, None, self.file_name, "Content", 128, "Type"
        )
        # File is correctly assigned to component
        assert_equal(component_file.node, component)
        # File does not overwrite parent project's version
        assert_equal(len(self.project.files_versions), 1)

    def test_uploader_is_user(self):
        assert_equal(self.node_file.uploader, self.user)

    def test_revise_content(self):
        user2 = UserFactory()
        updated_file = self.project.add_file(
            user2,
            None,
            self.file_name,
            "Content 2",
            129,
            "Type 2",
        )
        # There are two versions of the file
        assert_equal(len(self.project.files_versions[self.file_key]), 2)
        assert_equal(self.node_file.filename, updated_file.filename)
        # Each version has the correct user, size, and type
        assert_equal(self.node_file.uploader, self.user)
        assert_equal(updated_file.uploader, user2)
        assert_equal(self.node_file.size, 128)
        assert_equal(updated_file.size, 129)
        assert_equal(self.node_file.content_type, "Type")
        assert_equal(updated_file.content_type, "Type 2")


    @raises(FileNotModified)
    def test_not_modified(self):
        user2 = UserFactory()
        # Modify user, size, and type, but not content
        self.project.add_file(user2, None, self.file_name, "Content", 256,
                              "Type 2")


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
        assert_equal(wiki.page_name, "home")
        assert_equal(wiki.version, 1)
        assert_true(hasattr(wiki, "is_current"))
        assert_equal(wiki.content, 'Some content')
        assert_true(wiki.user)
        assert_true(wiki.node)

    def test_url(self):
        assert_equal(self.wiki.url, "{project_url}wiki/home/"
                                    .format(project_url=self.project.url))


class TestUpdateNodeWiki(DbTestCase):

    def setUp(self):
        # Create project with component
        self.user = UserFactory()
        self.project = ProjectFactory()
        self.node = NodeFactory(creator=self.user, project=self.project)
        # user updates the wiki
        self.project.update_node_wiki("home", "Hello world", self.user)
        self.versions = self.project.wiki_pages_versions

    def test_default_wiki(self):
        # There is no default wiki
        project1 = ProjectFactory()
        assert_equal(project1.get_wiki_page("home"), None)

    def test_default_is_current(self):
        assert_true(self.project.get_wiki_page('home').is_current)
        self.project.update_node_wiki("home", "Hello world 2", self.user)
        assert_true(self.project.get_wiki_page('home').is_current)
        self.project.update_node_wiki("home", "Hello world 3", self.user)

    def test_wiki_content(self):
        # Wiki has correct content
        assert_equal(self.project.get_wiki_page("home").content, "Hello world")
        # user updates the wiki a second time
        self.project.update_node_wiki('home', "Hola mundo", self.user)
        # Both versions have the expected content
        assert_equal(self.project.get_wiki_page("home", 2).content, "Hola mundo")
        assert_equal(self.project.get_wiki_page("home", 1).content, "Hello world")

    def test_current(self):
        # Wiki is current
        assert_true(self.project.get_wiki_page("home", 1).is_current)
        # user updates the wiki a second time
        self.project.update_node_wiki('home', "Hola mundo", self.user)
        # New version is current, old version is not
        assert_true(self.project.get_wiki_page("home", 2).is_current)
        assert_false(self.project.get_wiki_page("home", 1).is_current)

    def test_update_log(self):
        # Updates are logged
        assert_equal(self.project.logs[-1].action, "wiki_updated")
        # user updates the wiki a second time
        self.project.update_node_wiki('home', "Hola mundo", self.user)
        # There are two update logs
        assert_equal([log.action for log in self.project.logs].count('wiki_updated'), 2)

    def test_wiki_versions(self):
        # Number of versions is correct
        assert_equal(len(self.versions['home']), 1)
        # Update wiki
        self.project.update_node_wiki("home", "Hello world", self.user)
        # Number of versions is correct
        assert_equal(len(self.versions['home']), 2)
        # Versions are different
        assert_not_equal(self.versions['home'][0], self.versions['home'][1])

    def test_update_two_node_wikis(self):
        # user updates a second wiki for the same node
        self.project.update_node_wiki("second", "Hola mundo", self.user)
        # each wiki only has one version
        assert_equal(len(self.versions['home']), 1)
        assert_equal(len(self.versions['second']), 1)
        # There are 2 logs saved
        assert_equal([log.action for log in self.project.logs].count('wiki_updated'), 2)
        # Each wiki has the expected content
        assert_equal(self.project.get_wiki_page("home").content, "Hello world")
        assert_equal(self.project.get_wiki_page("second").content, "Hola mundo")


class TestNode(DbTestCase):

    def setUp(self):
        # Create project with component
        self.user = UserFactory()
        self.parent = ProjectFactory()
        self.node = NodeFactory(creator=self.user, project=self.parent)

    def test_node_factory(self):
        node = NodeFactory()
        assert_equal(node.category, 'hypothesis')
        assert_true(node.node__parent)
        assert_equal(node.logs[-1].action, 'node_created')

    def test_remove_node(self):
        # Add some components and delete the project
        component = NodeFactory(creator=self.user, project=self.node)
        subproject = ProjectFactory(creator=self.user, project=self.node)
        self.node.remove_node(self.user)
        # The correct nodes were deleted
        assert_true(self.node.is_deleted)
        assert_true(component.is_deleted)
        assert_false(subproject.is_deleted)
        assert_false(self.parent.is_deleted)
        # A log was saved
        assert_equal(self.parent.logs[-1].action, 'node_removed')

    def test_url(self):
        assert_equal(
            self.node.url,
            '/{0}/'.format(self.node._primary_key)
        )

    def test_watch_url(self):
        url = self.node.watch_url
        assert_equal(url, "/api/v1/project/{0}/node/{1}/watch/"
                                .format(self.parent._primary_key,
                                        self.node._primary_key))

    def test_parent_id(self):
        assert_equal(self.node.parent_id, self.parent._id)

    def test_parent(self):
        assert_equal(self.node.parent, self.parent)

    def test_in_parent_nodes(self):
        assert_in(self.node, self.parent.nodes)

    def test_log(self):
        latest_log = self.node.logs[-1]
        assert_equal(latest_log.action, 'node_created')
        assert_equal(latest_log.params, {
            'node': self.node._primary_key,
            'project': self.parent._primary_key,
        })
        assert_equal(latest_log.user, self.user)

    def test_add_file(self):
        #todo Add file series of tests
        pass


class TestProject(DbTestCase):

    def setUp(self):
        # Create project
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user, description='foobar')

    def test_project_factory(self):
        node = ProjectFactory()
        assert_equal(node.category, 'project')
        assert_true(node._id)
        assert_almost_equal(
            node.date_created, datetime.datetime.utcnow(),
            delta=datetime.timedelta(seconds=5),
        )
        assert_false(node.is_public)
        assert_false(node.is_deleted)
        assert_true(hasattr(node, 'deleted_date'))
        assert_false(node.is_registration)
        assert_true(hasattr(node, 'registered_date'))
        assert_false(node.is_fork)
        assert_true(hasattr(node, 'forked_date'))
        assert_true(node.title)
        assert_true(hasattr(node, 'description'))
        assert_true(hasattr(node, 'registration_list'))
        assert_true(hasattr(node, 'fork_list'))
        assert_true(hasattr(node, 'registered_meta'))
        assert_true(hasattr(node, 'registered_user'))
        assert_true(hasattr(node, 'registered_schema'))
        assert_true(node.creator)
        assert_true(node.contributors)
        assert_true(node.contributor_list)
        assert_equal(len(node.logs), 1)
        assert_true(hasattr(node, 'tags'))
        assert_true(hasattr(node, 'nodes'))
        assert_true(hasattr(node, 'forked_from'))
        assert_true(hasattr(node, 'registered_from'))
        assert_true(hasattr(node, 'api_keys'))
        assert_equal(node.logs[-1].action, 'project_created')

    def test_log(self):
        latest_log = self.project.logs[-1]
        assert_equal(latest_log.action, 'project_created')
        assert_equal(latest_log.params['project'], self.project._primary_key)
        assert_equal(latest_log.user, self.user)

    def test_url(self):
        assert_equal(
            self.project.url,
            '/{0}/'.format(self.project._primary_key)
        )

    def test_api_url(self):
        api_url = self.project.api_url
        assert_equal(api_url, "/api/v1/project/{0}/".format(self.project._primary_key))

    def test_watch_url(self):
        watch_url = self.project.watch_url
        assert_equal(watch_url, "/api/v1/project/{0}/watch/".format(self.project._primary_key))

    def test_parent_id(self):
        assert_false(self.project.parent_id)

    def test_watching(self):
        # A user watched a node
        user = UserFactory()
        config1 = WatchConfigFactory(node=self.project)
        user.watched.append(config1)
        user.save()
        assert_in(config1._id, self.project.watchconfig__watched)

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
        assert_not_in(user2._id, [contrib.get('id') for contrib in self.project.contributor_list])
        assert_equal(self.project.logs[-1].action, "contributor_removed")

    def test_add_private_link(self):
        link = self.project.add_private_link()
        assert_in(link, self.project.private_links)

    def test_remove_private_link(self):
        link = self.project.add_private_link()
        assert_in(link, self.project.private_links)
        self.project.remove_private_link(link)
        assert_not_in(link, self.project.private_links)

    def test_remove_nonregistered_contributor(self):
        nr_user = {
            'email': 'foo@bar.com',
            'name': 'Weezy F. Baby',
        }
        self.project.add_nonregistered_contributor(user=self.user, **nr_user)
        self.project.save()
        # The user is removed
        hash_id = hashlib.md5(nr_user['email']).hexdigest()
        self.project.remove_nonregistered_contributor(
            user=self.user, 
            api_key=None, 
            name=nr_user['name'], 
            hash_id=hash_id,
        )
        # List does not contain nonregistered contributor
        assert_not_in(nr_user, self.project.contributors)
        assert_equal(self.project.logs[-1].action, "contributor_removed")
        assert_not_in("Weezy F. Baby", [contrib.get('nr_name') for contrib in self.project.contributor_list])
        
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

    def test_noncontributor_cant_edit_public(self):
        user1 = UserFactory()
        # Change project to public
        self.project.set_permissions('public')
        self.project.save()
        # Noncontributor can't edit
        assert_false(self.project.can_edit(user1))

    def test_can_view_private(self):
        # Create contributor and noncontributor
        contributor = UserFactory()
        other_guy = UserFactory()
        self.project.add_contributor(contributor=contributor, user=self.user)
        link = self.project.add_private_link()
        self.project.save()
        # Only creator and contributor can view
        assert_true(self.project.can_view(self.user))
        assert_true(self.project.can_view(contributor))
        assert_false(self.project.can_view(other_guy))
        assert_true(self.project.can_view(other_guy, link))

    def test_can_view_public(self):
        # Create contributor and noncontributor
        contributor = UserFactory()
        other_guy = UserFactory()
        self.project.add_contributor(contributor=contributor, user=self.user)
        # Change project to public
        self.project.set_permissions('public')
        self.project.save()
        # Creator, contributor, and noncontributor can view
        assert_true(self.project.can_view(self.user))
        assert_true(self.project.can_view(contributor))
        assert_true(self.project.can_view(other_guy))

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

    def test_no_parent(self):
        assert_equal(self.project.parent, None)

    def test_get_recent_logs(self):
        # Add some logs
        for _ in range(5):
            self.project.logs.append(NodeLogFactory())
        # Expected logs appears
        assert_equal(
            self.project.get_recent_logs(3),
            list(reversed(self.project.logs)[:3])
        )
        assert_equal(
            self.project.get_recent_logs(),
            list(reversed(self.project.logs))
        )

    def test_date_modified(self):
        self.project.logs.append(NodeLogFactory())
        assert_equal(self.project.date_modified, self.project.logs[-1].date)
        assert_not_equal(self.project.date_modified, self.project.date_created)


class TestForkNode(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)

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
        assert_equal(original.parent is None, fork.parent is None)

        # Test modified fields
        assert_true(fork.is_fork)
        assert_equal(fork.forked_from, original)
        assert_in(fork._id, original.fork_list)
        assert_in(fork._id, original.node__forked)
        # Note: Must cast ForeignList to list for comparison
        assert_equal(list(fork.contributors), [fork_user])
        assert_equal(len(fork.contributor_list), 1)
        assert_in(
            fork_user._id,
            [user.get('id') for user in fork.contributor_list]
        )
        assert_true((fork_date - fork.date_created) < datetime.timedelta(seconds=5))
        assert_not_equal(fork.forked_date, original.date_created)

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

    def test_fork_recursion(self):
        """Omnibus test for forking.

        """
        # Make a some children
        self.component = NodeFactory(creator=self.user, project=self.project)
        self.subproject = ProjectFactory(creator=self.user, project=self.project)

        # Add files to test copying
        self.project.add_file(
            self.user, None, 'test.txt', 'test content', 4, 'text/plain'
        )
        self.component.add_file(
            self.user, None, 'test2.txt', 'test content2', 4, 'text/plain'
        )
        self.subproject.add_file(
            self.user, None, 'test3.txt', 'test content3', 4, 'text/plain'
        )

        # Log time
        fork_date = datetime.datetime.utcnow()

        # Fork node
        fork = self.project.fork_node(user=self.user)

        # Compare fork to original
        self._cmp_fork_original(self.user, fork_date, fork, self.project)

    def test_fork_private_children(self):
        """Tests that only public components are created

        """
        # Make project public
        self.project.set_permissions('public')
        # Make some children
        self.public_component = NodeFactory(
            creator=self.user,
            project=self.project,
            title='Forked',
            is_public=True,
        )
        self.public_subproject = ProjectFactory(
            creator=self.user,
            project=self.project,
            title='Forked',
            is_public=True,
        )
        self.private_component = NodeFactory(
            creator=self.user,
            project=self.project,
            title='Not Forked',
        )
        self.private_subproject = ProjectFactory(
            creator=self.user,
            project=self.project,
            title='Not Forked',
        )
        self.private_subproject_public_component = NodeFactory(
            creator=self.user,
            project=self.private_subproject,
            title='Not Forked',
        )
        self.public_subproject_public_component = NodeFactory(
            creator=self.user,
            project=self.private_subproject,
            title='Forked',
        )

        # New user forks the project
        fork = self.project.fork_node(user=UserFactory())

        # fork correct children
        assert_equal(len(fork.nodes), 2)
        assert_not_in('Not Forked', [node.title for node in fork.nodes])

    def test_fork_not_public(self):
        self.project.set_permissions('public')
        fork = self.project.fork_node(self.user)
        assert_false(fork.is_public)

    def test_cannot_fork_private_node(self):
        user2 = UserFactory()
        fork = self.project.fork_node(user2)
        assert_false(fork)

    def test_can_fork_public_node(self):
        self.project.set_permissions('public')
        user2 = UserFactory()
        fork = self.project.fork_node(user2)
        assert_true(fork)

    def test_contributor_can_fork(self):
        user2 = UserFactory()
        self.project.add_contributor(user2)
        fork = self.project.fork_node(user2)
        assert_true(fork)


class TestRegisterNode(DbTestCase):

    def setUp(self):
        ensure_schemas()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(project=self.project)

    def test_factory(self):
        # Create a registration with kwargs
        registration1 = RegistrationFactory(
            title="t1", description="d1", creator=self.user,
        )
        assert_equal(registration1.title, "t1")
        assert_equal(registration1.description, "d1")
        assert_equal(len(registration1.contributors), 1)
        assert_in(self.user, registration1.contributors)
        assert_equal(registration1.registered_user, self.user)
        assert_equal(len(registration1.registered_meta), 1)
        assert_true(registration1.registered_schema)

        # Create a registration from a project
        user2 = UserFactory()
        self.project.add_contributor(user2)
        registration2 = RegistrationFactory(
            project=self.project,
            user=user2,
            template="Template2",
            data="Something else",
        )
        assert_equal(registration2.registered_from, self.project)
        assert_equal(registration2.registered_user, user2)
        assert_equal(registration2.registered_meta["Template2"], "Something else")

        # Test default user
        assert_equal(self.registration.registered_user, self.user)


    def test_title(self):
        assert_equal(self.registration.title, self.project.title)

    def test_description(self):
        assert_equal(self.registration.description, self.project.description)

    def test_category(self):
        assert_equal(self.registration.category, self.project.category)

    def test_permissions(self):
        assert_false(self.registration.is_public)
        self.project.set_permissions('public')
        registration = RegistrationFactory(project=self.project)
        assert_true(registration.is_public)

    def test_contributors(self):
        assert_equal(self.registration.contributors, self.project.contributors)

    def test_contributors_list(self):
        assert_equal(
            self.registration.contributor_list,
            self.project.contributor_list,
        )

    def test_forked_from(self):
        # A a node that is not a fork
        assert_equal(self.registration.forked_from, None)
        # A node that is a fork
        fork = self.project.fork_node(self.user)
        registration = RegistrationFactory(project=fork)
        assert_equal(registration.forked_from, self.project)

    def test_creator(self):
        user2 = UserFactory()
        self.project.add_contributor(user2)
        registration = RegistrationFactory(project=self.project)
        assert_equal(registration.creator, self.user)

    def test_logs(self):
        # Registered node has all logs except the Project Registered log
        assert_equal(self.registration.logs, self.project.logs[:-1])

    def test_registration_log(self):
        assert_equal(self.project.logs[-1].action, 'project_registered')

    def test_tags(self):
        assert_equal(self.registration.tags, self.project.tags)

    def test_nodes(self):

        # Create some nodes
        self.component = NodeFactory(
            creator=self.user,
            project=self.project,
            title='Title1',
        )
        self.subproject = ProjectFactory(
            creator=self.user,
            project=self.project,
            title='Title2',
        )
        self.subproject_component = NodeFactory(
            creator=self.user,
            project=self.subproject,
            title='Title3',
        )

        # Make a registration
        registration = RegistrationFactory(project=self.project)

        # Registration has the nodes
        assert_equal(len(registration.nodes), 2)
        assert_equal(
            [node.title for node in registration.nodes],
            [node.title for node in self.project.nodes],
        )
        # Nodes are copies and not the original versions
        for node in registration.nodes:
            assert_not_in(node, self.project.nodes)
            assert_true(node.is_registration)

    def test_partial_contributor_registration(self):

        # Create some nodes
        self.component = NodeFactory(
            creator=self.user,
            project=self.project,
            title='Not Registered',
        )
        self.subproject = ProjectFactory(
            creator=self.user,
            project=self.project,
            title='Not Registered',
        )

        # Create some nodes to share
        self.shared_component = NodeFactory(
            creator=self.user,
            project=self.project,
            title='Registered',
        )
        self.shared_subproject = ProjectFactory(
            creator=self.user,
            project=self.project,
            title='Registered',
        )

        # Share the project and some nodes
        user2 = UserFactory()
        self.project.add_contributor(user2)
        self.shared_component.add_contributor(user2)
        self.shared_subproject.add_contributor(user2)

        # Partial contributor registers the node
        registration = RegistrationFactory(project=self.project, user=user2)

        # The correct subprojects were registered
        assert_equal(len(registration.nodes), 2)
        assert_not_in(
            'Not Registered',
            [node.title for node in registration.nodes],
        )

    def test_is_registration(self):
        assert_true(self.registration.is_registration)

    def test_registered_date(self):
        assert_almost_equal(
            self.registration.registered_date,
            datetime.datetime.utcnow(),
            delta=datetime.timedelta(seconds=5),
        )

    def test_registered_meta(self):
        assert_equal(self.registration.registered_meta['Template1'],
                     'Some words')

    def test_registered_user(self):
        # Add a second contributor
        user2 = UserFactory()
        self.project.add_contributor(user2)
        # Second contributor registers project
        registration = RegistrationFactory(project=self.project, user=user2)
        assert_equal(registration.registered_user, user2)

    def test_registered_from(self):
        assert_equal(self.registration.registered_from, self.project)

    def test_registration_list(self):
        assert_in(self.registration._id, self.project.registration_list)


class TestNodeLog(DbTestCase):

    def setUp(self):
        self.log = NodeLogFactory()

    def test_node_log_factory(self):
        log = NodeLogFactory()
        assert_true(log.action)

    def test_serialize(self):
        node = NodeFactory(category="hypothesis")
        log = NodeLogFactory(params={'node': node._primary_key})
        node.logs.append(log)
        node.save()
        d = log.serialize()
        assert_equal(d['action'], log.action)
        assert_equal(d['node']['category'], 'component')
        assert_equal(d['node']['url'], log.node.url)
        assert_equal(d['date'], utils.rfcformat(log.date))
        assert_in('contributors', d)
        assert_equal(d['user']['fullname'], log.user.fullname)
        assert_equal(d['user']['url'], log.user.url)
        assert_in('api_key', d)
        assert_equal(d['params'], log.params)
        assert_equal(d['node']['title'], log.node.title)

    def test_tz_date(self):
        assert_equal(self.log.tz_date.tzinfo, pytz.UTC)

    def test_formatted_date(self):
        iso_formatted = self.log.formatted_date  # The string version in iso format
        # Reparse the date
        parsed = parser.parse(iso_formatted)
        assert_equal(parsed, self.log.tz_date)


class TestWatchConfig(DbTestCase):

    def tearDown(self):
        User.remove()

    def test_factory(self):
        config = WatchConfigFactory(digest=True, immediate=False)
        assert_true(config.digest)
        assert_false(config.immediate)
        assert_true(config.node._id)


class TestUnregisteredUser(unittest.TestCase):
    def test_factory(self):
        u1 = UnregUserFactory()
        assert_true(u1['nr_name'])
        assert_true(u1['nr_email'])
        u2 = UnregUserFactory()
        assert_not_equal(u1['nr_name'], u2['nr_name'])

if __name__ == '__main__':
    unittest.main()
