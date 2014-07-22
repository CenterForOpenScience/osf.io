# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''

import mock
import unittest
from nose.tools import *  # PEP8 asserts

import pytz
import datetime
import urlparse
from dateutil import parser

from modularodm.exceptions import ValidationError, ValidationValueError, ValidationTypeError


from framework.analytics import get_total_activity_count
from framework.exceptions import PermissionsError
from framework.auth import User, Auth
from framework.auth.utils import impute_names_model
from framework import utils
from framework.bcrypt import check_password_hash
from framework.git.exceptions import FileNotModified
from website import filters, language, settings
from website.exceptions import NodeStateError
from website.profile.utils import serialize_user
from website.project.model import (
    ApiKey, Comment, Node, NodeLog, Pointer, ensure_schemas, has_anonymous_link
)
from website.app import init_app
from website.addons.osffiles.model import NodeFile
from website.util.permissions import CREATOR_PERMISSIONS
from website.util import web_url_for, api_url_for

from tests.base import OsfTestCase, Guid, fake, URLLookup
from tests.factories import (
    UserFactory, ApiKeyFactory, NodeFactory, PointerFactory,
    ProjectFactory, NodeLogFactory, WatchConfigFactory,
    NodeWikiFactory, RegistrationFactory, UnregUserFactory,
    ProjectWithAddonFactory, UnconfirmedUserFactory, CommentFactory, PrivateLinkFactory,
    AuthUserFactory
)

app = init_app(set_backends=False, routes=True)
lookup = URLLookup(app)

GUID_FACTORIES = UserFactory, NodeFactory, ProjectFactory


class TestUserValidation(OsfTestCase):

    def setUp(self):
        super(TestUserValidation, self).setUp()
        self.user = AuthUserFactory()

    def test_validate_fullname_none(self):
        self.user.fullname = None
        with assert_raises(ValidationError):
            self.user.save()

    def test_validate_fullname_empty(self):
        self.user.fullname = ''
        with assert_raises(ValidationValueError):
            self.user.save()

    def test_validate_social_personal_empty(self):
        self.user.social = {'personal_site': ''}
        try:
            self.user.save()
        except:
            assert 0

    def test_validate_social_valid(self):
        self.user.social = {'personal_site': 'http://cos.io/'}
        try:
            self.user.save()
        except:
            assert 0

    def test_validate_social_personal_invalid(self):
        self.user.social = {'personal_site': 'help computer'}
        with assert_raises(ValidationError):
            self.user.save()

    def test_validate_jobs_valid(self):
        self.user.jobs = [{
            'institution': 'School of Lover Boys',
            'department': 'Fancy Patter',
            'position': 'Lover Boy',
            'start': datetime.datetime(1970, 1, 1),
            'end': datetime.datetime(1980, 1, 1),
        }]
        try:
            self.user.save()
        except:
            assert 0

    def test_validate_jobs_institution_empty(self):
        self.user.jobs = [{'institution': ''}]
        with assert_raises(ValidationError):
            self.user.save()

    def test_validate_jobs_bad_end_date(self):
        self.user.jobs = [{
            'institution': 'School of Lover Boys',
            'department': 'Fancy Patter',
            'position': 'Lover Boy',
            'start': datetime.datetime(1970, 1, 1),
            'end': datetime.datetime(1960, 1, 1),
        }]
        with assert_raises(ValidationValueError):
            self.user.save()


class TestUser(OsfTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)

    def test_update_guessed_names(self):
        name = fake.name()
        u = User(fullname=name)
        u.update_guessed_names()
        u.save()

        parsed = impute_names_model(name)
        assert_equal(u.fullname, name)
        assert_equal(u.given_name, parsed['given_name'])
        assert_equal(u.middle_names, parsed['middle_names'])
        assert_equal(u.family_name, parsed['family_name'])
        assert_equal(u.suffix, parsed['suffix'])

    def test_non_registered_user_is_not_active(self):
        u = User(username=fake.email(),
                 fullname='Freddie Mercury',
                 is_registered=False)
        u.set_password('killerqueen')
        u.save()
        assert_false(u.is_active())

    def test_create_unregistered(self):
        name, email = fake.name(), fake.email()
        u = User.create_unregistered(email=email,
                                     fullname=name)
        u.save()
        assert_equal(u.username, email)
        assert_false(u.is_registered)
        assert_true(email in u.emails)
        parsed = impute_names_model(name)
        assert_equal(u.given_name, parsed['given_name'])

    @mock.patch('framework.auth.core.User.update_search')
    def test_search_not_updated_for_unreg_users(self, update_search):
        u = User.create_unregistered(fullname=fake.name(), email=fake.email())
        u.save()
        assert update_search.called

    @mock.patch('framework.auth.core.User.update_search')
    def test_search_updated_for_registered_users(self, update_search):
        UserFactory(is_registered=True)
        assert_true(update_search.called)

    def test_create_unregistered_raises_error_if_already_in_db(self):
        u = UnregUserFactory()
        dupe = User.create_unregistered(fullname=fake.name(), email=u.username)
        with assert_raises(ValidationValueError):
            dupe.save()

    def test_user_with_no_password_is_not_active(self):
        u = User(
            username=fake.email(),
            fullname='Freddie Mercury',
            is_registered=True,
        )
        u.save()
        assert_false(u.is_active())

    def test_merged_user_is_not_active(self):
        master = UserFactory()
        dupe = UserFactory(merged_by=master)
        assert_false(dupe.is_active())

    def test_cant_create_user_without_username(self):
        u = User()  # No username given
        with assert_raises(ValidationError):
            u.save()

    def test_date_registered_upon_saving(self):
        u = User(username=fake.email(), fullname='Foo bar')
        u.save()
        assert_true(u.date_registered)

    def test_create(self):
        name, email = fake.name(), fake.email()
        user = User.create(
            username=email, password='foobar', fullname=name
        )
        user.save()
        assert_true(user.check_password('foobar'))
        assert_true(user._id)
        assert_equal(user.given_name, impute_names_model(name)['given_name'])

    def test_create_unconfirmed(self):
        name, email = fake.name(), fake.email()
        user = User.create_unconfirmed(
            username=email, password='foobar', fullname=name
        )
        user.save()
        assert_false(user.is_registered)
        assert_equal(len(user.email_verifications.keys()), 1)
        assert_equal(
            len(user.emails),
            0,
            'primary email has not been added to emails list'
        )

    def test_create_confirmed(self):
        name, email = fake.name(), fake.email()
        user = User.create_confirmed(
            username=email, password='foobar', fullname=name
        )
        user.save()
        assert_true(user.is_registered)
        assert_true(user.is_claimed)
        assert_equal(user.date_registered, user.date_confirmed)

    def test_cant_create_user_without_full_name(self):
        u = User(username=fake.email())
        with assert_raises(ValidationError):
            u.save()

    @mock.patch('website.security.random_string')
    def test_add_email_verification(self, random_string):
        random_string.return_value = '12345'
        u = UserFactory()
        assert_equal(len(u.email_verifications.keys()), 0)
        u.add_email_verification('foo@bar.com')
        assert_equal(len(u.email_verifications.keys()), 1)
        assert_equal(u.email_verifications['12345']['email'], 'foo@bar.com')

    @mock.patch('website.security.random_string')
    def test_get_confirmation_token(self, random_string):
        random_string.return_value = '12345'
        u = UserFactory()
        u.add_email_verification('foo@bar.com')
        assert_equal(u.get_confirmation_token('foo@bar.com'), '12345')

    @mock.patch('website.security.random_string')
    def test_get_confirmation_url(self, random_string):
        random_string.return_value = 'abcde'
        u = UserFactory()
        u.add_email_verification('foo@bar.com')
        assert_equal(u.get_confirmation_url('foo@bar.com'),
                '{0}confirm/{1}/{2}/'.format(settings.DOMAIN, u._primary_key, 'abcde'))

    def test_confirm_primary_email(self):
        u = UserFactory.build(username='foo@bar.com')
        u.is_registered = False
        u.is_claimed = False
        u.add_email_verification('foo@bar.com')
        u.save()
        token = u.get_confirmation_token('foo@bar.com')
        confirmed = u.confirm_email(token)
        u.save()
        assert_true(confirmed)
        assert_equal(len(u.email_verifications.keys()), 0)
        assert_in('foo@bar.com', u.emails)
        assert_true(u.is_registered)
        assert_true(u.is_claimed)

    def test_verify_confirmation_token(self):
        u = UserFactory.build()
        u.add_email_verification('foo@bar.com')
        u.save()
        assert_false(u.verify_confirmation_token('badtoken'))
        valid_token = u.get_confirmation_token('foo@bar.com')
        assert_true(u.verify_confirmation_token(valid_token))

    def test_factory(self):
        # Clear users
        Node.remove()
        User.remove()
        user = UserFactory()
        assert_equal(User.find().count(), 1)
        assert_true(user.username)
        another_user = UserFactory(username='joe@example.com')
        assert_equal(another_user.username, 'joe@example.com')
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
        user = User(username=fake.email(), fullname='Nick Cage')
        user.set_password('ghostrider')
        user.save()
        assert_true(check_password_hash(user.password, 'ghostrider'))

    def test_check_password(self):
        user = User(username=fake.email(), fullname='Nick Cage')
        user.set_password('ghostrider')
        user.save()
        assert_true(user.check_password('ghostrider'))
        assert_false(user.check_password('ghostride'))

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
        assert_equal(d.get('username', None), None)
        assert_equal(d['fullname'], user.fullname)
        assert_equal(d['registered'], user.is_registered)
        assert_equal(d['absolute_url'], user.absolute_url)
        assert_equal(d['date_registered'], user.date_registered.strftime('%Y-%m-%d'))
        assert_equal(d['active'], user.is_active())

    def test_serialize_user_full(self):
        master = UserFactory()
        user = UserFactory.build()
        master.merge_user(user, save=True)
        d = serialize_user(user, full=True)
        assert_equal(d['id'], user._primary_key)
        assert_equal(d['url'], user.url)
        assert_equal(d.get('username'), None)
        assert_equal(d['fullname'], user.fullname)
        assert_equal(d['registered'], user.is_registered)
        assert_equal(d['gravatar_url'], user.gravatar_url)
        assert_equal(d['absolute_url'], user.absolute_url)
        assert_equal(d['date_registered'], user.date_registered.strftime('%Y-%m-%d'))
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

        assert_true(hasattr(self.user, 'recently_added'))

        # Two users added as contributors
        user2 = UserFactory()
        user3 = UserFactory()
        project.add_contributor(contributor=user2, auth=self.consolidate_auth)
        project.add_contributor(contributor=user3, auth=self.consolidate_auth)
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
        project.add_contributor(contributor=user2, auth=self.consolidate_auth)
        project.add_contributor(contributor=user3, auth=self.consolidate_auth)

        # Users 2 and 3 are added to original project
        project2.add_contributor(contributor=user2, auth=self.consolidate_auth)
        project2.add_contributor(contributor=user4, auth=self.consolidate_auth)

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
            project.add_contributor(
                contributor=UserFactory(),
                auth=self.consolidate_auth
            )

        assert_equal(len(self.user.recently_added), 15)

    def test_display_full_name_registered(self):
        u = UserFactory()
        assert_equal(u.display_full_name(), u.fullname)

    def test_display_full_name_unregistered(self):
        name = fake.name()
        u = UnregUserFactory()
        project =ProjectFactory()
        project.add_unregistered_contributor(fullname=name, email=u.username,
            auth=Auth(project.creator))
        project.save()
        assert_equal(u.display_full_name(node=project), name)

    def test_get_projects_in_common(self):
        user2 = UserFactory()
        project = ProjectFactory(creator=self.user)
        project.add_contributor(contributor=user2, auth=self.consolidate_auth)
        project.save()

        project_keys = set(self.user.node__contributed._to_primary_keys())
        projects = set(self.user.node__contributed)

        assert_equal(self.user.get_projects_in_common(user2, primary_keys=True),
                     project_keys.intersection(user2.node__contributed._to_primary_keys()))
        assert_equal(self.user.get_projects_in_common(user2, primary_keys=False),
                     projects.intersection(user2.node__contributed))

    def test_n_projects_in_common(self):
        user2 = UserFactory()
        user3 = UserFactory()
        project = ProjectFactory(creator=self.user)

        project.add_contributor(contributor=user2, auth=self.consolidate_auth)
        project.save()

        assert_equal(self.user.n_projects_in_common(user2), 1)
        assert_equal(self.user.n_projects_in_common(user3), 0)


class TestUserParse(unittest.TestCase):

    def test_parse_first_last(self):
        parsed = impute_names_model('John Darnielle')
        assert_equal(parsed['given_name'], 'John')
        assert_equal(parsed['family_name'], 'Darnielle')

    def test_parse_first_last_particles(self):
        parsed = impute_names_model('John van der Slice')
        assert_equal(parsed['given_name'], 'John')
        assert_equal(parsed['family_name'], 'van der Slice')


class TestMergingUsers(OsfTestCase):

    def setUp(self):
        self.master = UserFactory(fullname='Joe Shmo',
                            is_registered=True,
                            emails=['joe@example.com'])
        self.dupe = UserFactory(fullname='Joseph Shmo',
                            emails=['joseph123@hotmail.com'])

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
        assert_in('joseph123@hotmail.com', self.master.emails)

    def test_inherits_projects_contributed_by_dupe(self):
        project = ProjectFactory()
        project.add_contributor(self.dupe)
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

    def test_merging_dupe_who_is_contributor_on_same_projects(self):
        # Both master and dupe are contributors on the same project
        project = ProjectFactory()
        project.add_contributor(contributor=self.master)
        project.add_contributor(contributor=self.dupe)
        project.save()
        self._merge_dupe()  # perform the merge
        assert_true(project.is_contributor(self.master))
        assert_false(project.is_contributor(self.dupe))
        assert_equal(len(project.contributors), 2) # creator and master
                                                   # are the only contribs


class TestGUID(OsfTestCase):

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


class TestNodeFile(OsfTestCase):

    def setUp(self):
        # Create a project with a NodeFile
        self.node = ProjectFactory()
        self.node_file = NodeFile(node=self.node, path='foo.py', filename='foo.py', size=128)
        self.node.files_versions[self.node_file.clean_filename] = [self.node_file._primary_key]
        self.node.save()

    def test_url(self):
        assert_equal(
            self.node_file.api_url(self.node),
            '{0}osffiles/{1}/'.format(self.node.api_url, self.node_file.filename),
        )

    def test_clean(self):
        assert_equal(self.node_file.clean_filename, 'foo_py')

    def test_latest_version_number(self):
        assert_equal(self.node_file.latest_version_number(self.node), 1)

    def test_download_url(self):
        assert_equal(
            self.node_file.download_url(self.node),
            self.node.url + 'osffiles/{0}/version/1/download/'.format(self.node_file.filename)
        )


class TestAddFile(OsfTestCase):

    def setUp(self):
        # Create a project
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.user2 = UserFactory()
        self.consolidate_auth2 = Auth(user=self.user2)
        self.project = ProjectFactory(creator=self.user)
        # Add a file
        self.file_name = 'foo.py'
        self.file_key = self.file_name.replace('.', '_')
        self.node_file = self.project.add_file(
            self.consolidate_auth, self.file_name, 'Content', 128, 'Type'
        )
        self.project.save()

    def test_added(self):
        assert_equal(len(self.project.files_versions), 1)

    def test_component_add_file(self):
        # Add exact copy of parent project's file to component
        component = NodeFactory(project=self.project, creator=self.user)
        component_file = component.add_file(
            self.consolidate_auth, self.file_name, 'Content', 128, 'Type'
        )
        # File is correctly assigned to component
        assert_equal(component_file.node, component)
        # File does not overwrite parent project's version
        assert_equal(len(self.project.files_versions), 1)

    def test_uploader_is_user(self):
        assert_equal(self.node_file.uploader, self.user)

    def test_revise_content(self):
        user2 = UserFactory()
        consolidate_auth2 = Auth(user=user2)
        updated_file = self.project.add_file(
            consolidate_auth2,
            self.file_name,
            'Content 2',
            129,
            'Type 2',
        )
        # There are two versions of the file
        assert_equal(len(self.project.files_versions[self.file_key]), 2)
        assert_equal(self.node_file.filename, updated_file.filename)
        # Each version has the correct user, size, and type
        assert_equal(self.node_file.uploader, self.user)
        assert_equal(updated_file.uploader, user2)
        assert_equal(self.node_file.size, 128)
        assert_equal(updated_file.size, 129)
        assert_equal(self.node_file.content_type, 'Type')
        assert_equal(updated_file.content_type, 'Type 2')


    @raises(FileNotModified)
    def test_not_modified(self):

        # Modify user, size, and type, but not content
        self.project.add_file(self.consolidate_auth2, self.file_name, 'Content', 256,
                              'Type 2')


class TestApiKey(OsfTestCase):

    def test_factory(self):
        key = ApiKeyFactory()
        user = UserFactory()
        user.api_keys.append(key)
        user.save()
        assert_equal(len(user.api_keys), 1)
        assert_equal(ApiKey.find().count(), 1)


class TestNodeWikiPage(OsfTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.wiki = NodeWikiFactory(user=self.user, node=self.project)

    def test_factory(self):
        wiki = NodeWikiFactory()
        assert_equal(wiki.page_name, 'home')
        assert_equal(wiki.version, 1)
        assert_true(hasattr(wiki, 'is_current'))
        assert_equal(wiki.content, 'Some content')
        assert_true(wiki.user)
        assert_true(wiki.node)

    def test_url(self):
        assert_equal(self.wiki.url, '{project_url}wiki/home/'
                                    .format(project_url=self.project.url))


class TestUpdateNodeWiki(OsfTestCase):

    def setUp(self):
        # Create project with component
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory()
        self.node = NodeFactory(creator=self.user, project=self.project)
        # user updates the wiki
        self.project.update_node_wiki('home', 'Hello world', self.consolidate_auth)
        self.versions = self.project.wiki_pages_versions

    def test_default_wiki(self):
        # There is no default wiki
        project1 = ProjectFactory()
        assert_equal(project1.get_wiki_page('home'), None)

    def test_default_is_current(self):
        assert_true(self.project.get_wiki_page('home').is_current)
        self.project.update_node_wiki('home', 'Hello world 2', self.consolidate_auth)
        assert_true(self.project.get_wiki_page('home').is_current)
        self.project.update_node_wiki('home', 'Hello world 3', self.consolidate_auth)

    def test_wiki_content(self):
        # Wiki has correct content
        assert_equal(self.project.get_wiki_page('home').content, 'Hello world')
        # user updates the wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.consolidate_auth)
        # Both versions have the expected content
        assert_equal(self.project.get_wiki_page('home', 2).content, 'Hola mundo')
        assert_equal(self.project.get_wiki_page('home', 1).content, 'Hello world')

    def test_current(self):
        # Wiki is current
        assert_true(self.project.get_wiki_page('home', 1).is_current)
        # user updates the wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.consolidate_auth)
        # New version is current, old version is not
        assert_true(self.project.get_wiki_page('home', 2).is_current)
        assert_false(self.project.get_wiki_page('home', 1).is_current)

    def test_update_log(self):
        # Updates are logged
        assert_equal(self.project.logs[-1].action, 'wiki_updated')
        # user updates the wiki a second time
        self.project.update_node_wiki('home', 'Hola mundo', self.consolidate_auth)
        # There are two update logs
        assert_equal([log.action for log in self.project.logs].count('wiki_updated'), 2)

    def test_wiki_versions(self):
        # Number of versions is correct
        assert_equal(len(self.versions['home']), 1)
        # Update wiki
        self.project.update_node_wiki('home', 'Hello world', self.consolidate_auth)
        # Number of versions is correct
        assert_equal(len(self.versions['home']), 2)
        # Versions are different
        assert_not_equal(self.versions['home'][0], self.versions['home'][1])

    def test_update_two_node_wikis(self):
        # user updates a second wiki for the same node
        self.project.update_node_wiki('second', 'Hola mundo', self.consolidate_auth)
        # each wiki only has one version
        assert_equal(len(self.versions['home']), 1)
        assert_equal(len(self.versions['second']), 1)
        # There are 2 logs saved
        assert_equal([log.action for log in self.project.logs].count('wiki_updated'), 2)
        # Each wiki has the expected content
        assert_equal(self.project.get_wiki_page('home').content, 'Hello world')
        assert_equal(self.project.get_wiki_page('second').content, 'Hola mundo')


class TestNode(OsfTestCase):

    def setUp(self):
        # Create project with component
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.parent = ProjectFactory(creator=self.user)
        self.node = NodeFactory(creator=self.user, project=self.parent)

    def test_validate_categories(self):
        with assert_raises(ValidationError):
            Node(category='invalid').save()  # an invalid category

    def test_web_url_for(self):
        with app.test_request_context():
            result = self.parent.web_url_for('view_project')
            assert_equal(result, web_url_for('view_project', pid=self.parent._primary_key))

            result2 = self.node.web_url_for('view_project')
            assert_equal(result2, web_url_for('view_project', pid=self.parent._primary_key,
                nid=self.node._primary_key))

    def test_category_display(self):
        node = NodeFactory(category='hypothesis')
        assert_equal(node.category_display, 'Hypothesis')
        node2 = NodeFactory(category='methods and measures')
        assert_equal(node2.category_display, 'Methods and Measures')


    def test_api_url_for(self):
        with app.test_request_context():
            result = self.parent.api_url_for('view_project')
            assert_equal(result, api_url_for('view_project', pid=self.parent._primary_key))

            result2 = self.node.api_url_for('view_project')
            assert_equal(result2, api_url_for('view_project', pid=self.parent._primary_key,
                nid=self.node._primary_key))

    def test_node_factory(self):
        node = NodeFactory()
        assert_equal(node.category, 'hypothesis')
        assert_true(node.node__parent)
        assert_equal(node.logs[-1].action, 'node_created')
        assert_equal(
            set(node.get_addon_names()),
            set([
                addon_config.short_name
                for addon_config in settings.ADDONS_AVAILABLE
                if 'node' in addon_config.added_default
            ])
        )
        for addon_config in settings.ADDONS_AVAILABLE:
            if 'node' in addon_config.added_default:
                assert_in(
                    addon_config.short_name,
                    node.get_addon_names()
                )
                assert_true(
                    len([
                        addon
                        for addon in node.addons
                        if addon.config.short_name == addon_config.short_name
                    ]),
                    1
                )

    def test_add_addon(self):
        addon_count = len(self.node.get_addon_names())
        addon_record_count = len(self.node.addons)
        added = self.node.add_addon('github', self.consolidate_auth)
        assert_true(added)
        self.node.reload()
        assert_equal(
            len(self.node.get_addon_names()),
            addon_count + 1
        )
        assert_equal(
            len(self.node.addons),
            addon_record_count + 1
        )
        assert_equal(
            self.node.logs[-1].action,
            NodeLog.ADDON_ADDED
        )

    def test_add_existing_addon(self):
        addon_count = len(self.node.get_addon_names())
        addon_record_count = len(self.node.addons)
        added = self.node.add_addon('osffiles', self.consolidate_auth)
        assert_false(added)
        assert_equal(
            len(self.node.get_addon_names()),
            addon_count
        )
        assert_equal(
            len(self.node.addons),
            addon_record_count
        )

    def test_delete_addon(self):
        addon_count = len(self.node.get_addon_names())
        deleted = self.node.delete_addon('wiki', self.consolidate_auth)
        assert_true(deleted)
        assert_equal(
            len(self.node.get_addon_names()),
            addon_count - 1
        )
        assert_equal(
            self.node.logs[-1].action,
            NodeLog.ADDON_REMOVED
        )

    @mock.patch('website.addons.github.model.AddonGitHubNodeSettings.config')
    def test_delete_mandatory_addon(self, mock_config):
        mock_config.added_mandatory = ['node']
        self.node.add_addon('github', self.consolidate_auth)
        with assert_raises(ValueError):
            self.node.delete_addon('github', self.consolidate_auth)

    def test_delete_nonexistent_addon(self):
        addon_count = len(self.node.get_addon_names())
        deleted = self.node.delete_addon('github', self.consolidate_auth)
        assert_false(deleted)
        assert_equal(
            len(self.node.get_addon_names()),
            addon_count
        )

    def test_cant_add_component_to_component(self):
        with assert_raises(ValueError):
            NodeFactory(project=self.node)

    def test_url(self):
        assert_equal(
            self.node.url,
            '/{0}/'.format(self.node._primary_key)
        )

    def test_watch_url(self):
        url = self.node.watch_url
        assert_equal(url, '/api/v1/project/{0}/node/{1}/watch/'
                                .format(self.parent._primary_key,
                                        self.node._primary_key))

    def test_parent_id(self):
        assert_equal(self.node.parent_id, self.parent._id)

    def test_parent(self):
        assert_equal(self.node.parent_node, self.parent)

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

    def test_add_pointer(self):
        node2 = NodeFactory(creator=self.user)
        pointer = self.node.add_pointer(node2, auth=self.consolidate_auth)
        assert_equal(pointer, self.node.nodes[0])
        assert_equal(len(self.node.nodes), 1)
        assert_false(self.node.nodes[0].primary)
        assert_equal(self.node.nodes[0].node, node2)
        assert_equal(node2.points, 1)
        assert_equal(
            self.node.logs[-1].action, NodeLog.POINTER_CREATED
        )
        assert_equal(
            self.node.logs[-1].params, {
                'project': self.node.parent_id,
                'node': self.node._primary_key,
                'pointer': {
                    'id': pointer.node._id,
                    'url': pointer.node.url,
                    'title': pointer.node.title,
                    'category': pointer.node.category,
                },
            }
        )

    def test_add_pointer_already_present(self):
        node2 = NodeFactory(creator=self.user)
        self.node.add_pointer(node2, auth=self.consolidate_auth)
        with assert_raises(ValueError):
            self.node.add_pointer(node2, auth=self.consolidate_auth)

    def test_rm_pointer(self):
        node2 = NodeFactory(creator=self.user)
        pointer = self.node.add_pointer(node2, auth=self.consolidate_auth)
        self.node.rm_pointer(pointer, auth=self.consolidate_auth)
        assert_equal(len(self.node.nodes), 0)
        assert_equal(node2.points, 0)
        assert_equal(
            self.node.logs[-1].action, NodeLog.POINTER_REMOVED
        )
        assert_equal(
            self.node.logs[-1].params, {
                'project': self.node.parent_id,
                'node': self.node._primary_key,
                'pointer': {
                    'id': pointer.node._id,
                    'url': pointer.node.url,
                    'title': pointer.node.title,
                    'category': pointer.node.category,
                },
            }
        )

    def test_rm_pointer_not_present(self):
        node2 = NodeFactory(creator=self.user)
        pointer = Pointer(node=node2)
        with assert_raises(ValueError):
            self.node.rm_pointer(pointer, auth=self.consolidate_auth)

    def test_fork_pointer_not_present(self):
        pointer = PointerFactory()
        with assert_raises(ValueError):
            self.node.fork_pointer(pointer, auth=self.consolidate_auth)

    def _fork_pointer(self, content):
        pointer = self.node.add_pointer(content, auth=self.consolidate_auth)
        forked = self.node.fork_pointer(pointer, auth=self.consolidate_auth)
        assert_true(forked.is_fork)
        assert_equal(forked.forked_from, content)
        assert_true(self.node.nodes[-1].primary)
        assert_equal(self.node.nodes[-1], forked)
        assert_equal(
            self.node.logs[-1].action, NodeLog.POINTER_FORKED
        )
        assert_equal(
            self.node.logs[-1].params, {
                'project': self.node.parent_id,
                'node': self.node._primary_key,
                'pointer': {
                    'id': pointer.node._id,
                    'url': pointer.node.url,
                    'title': pointer.node.title,
                    'category': pointer.node.category,
                },
            }
        )

    def test_fork_pointer_project(self):
        project = ProjectFactory(creator=self.user)
        self._fork_pointer(project)

    def test_fork_pointer_component(self):
        component = NodeFactory(creator=self.user)
        self._fork_pointer(component)

    def test_add_file(self):
        #todo Add file series of tests
        pass


class TestRemoveNode(OsfTestCase):

    def setUp(self):
        # Create project with component
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.parent_project = ProjectFactory(creator=self.user)
        self.project = ProjectFactory(creator=self.user,
                                      project=self.parent_project)

    def test_remove_project_without_children(self):
        self.project.remove_node(auth=self.consolidate_auth)

        assert_true(self.project.is_deleted)
        # parent node should have a log of the event
        assert_equal(self.parent_project.logs[-1].action, 'node_removed')

    def test_remove_project_with_project_child_fails(self):
        with assert_raises(NodeStateError):
            self.parent_project.remove_node(self.consolidate_auth)

    def test_remove_project_with_component_child_fails(self):
        NodeFactory(creator=self.user, project=self.project)

        with assert_raises(NodeStateError):
            self.parent_project.remove_node(self.consolidate_auth)

    def test_remove_project_with_pointer_child(self):
        target = ProjectFactory(creator=self.user)
        self.project.add_pointer(node=target, auth=self.consolidate_auth)

        assert_equal(len(self.project.nodes), 1)

        self.project.remove_node(auth=self.consolidate_auth)

        assert_true(self.project.is_deleted)
        # parent node should have a log of the event
        assert_equal(self.parent_project.logs[-1].action, 'node_removed')

        # target node shouldn't be deleted
        assert_false(target.is_deleted)


class TestAddonCallbacks(OsfTestCase):
    """Verify that callback functions are called at the right times, with the
    right arguments.

    """
    callbacks = {
        'after_remove_contributor': None,
        'after_set_privacy': None,
        'after_fork': (None, None),
        'after_register': (None, None),
    }

    def setUp(self):

        # Create project with component
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.parent = ProjectFactory()
        self.node = NodeFactory(creator=self.user, project=self.parent)

        # Mock addon callbacks
        for addon in self.node.addons:
            mock_settings = mock.create_autospec(addon.__class__)
            for callback, return_value in self.callbacks.iteritems():
                mock_callback = getattr(mock_settings, callback)
                mock_callback.return_value = return_value
                setattr(
                    addon,
                    callback,
                    getattr(mock_settings, callback)
                )

    def test_remove_contributor_callback(self):

        user2 = UserFactory()
        self.node.add_contributor(contributor=user2, auth=self.consolidate_auth)
        self.node.remove_contributor(contributor=user2, auth=self.consolidate_auth)
        for addon in self.node.addons:
            callback = addon.after_remove_contributor
            callback.assert_called_once_with(
                self.node, user2
            )

    def test_set_privacy_callback(self):

        self.node.set_privacy('public', self.consolidate_auth)
        for addon in self.node.addons:
            callback = addon.after_set_privacy
            callback.assert_called_with(
                self.node, 'public',
            )

        self.node.set_privacy('private', self.consolidate_auth)
        for addon in self.node.addons:
            callback = addon.after_set_privacy
            callback.assert_called_with(
                self.node, 'private'
            )

    def test_fork_callback(self):
        fork = self.node.fork_node(auth=self.consolidate_auth)
        for addon in self.node.addons:
            callback = addon.after_fork
            callback.assert_called_once_with(
                self.node, fork, self.user
            )

    def test_register_callback(self):
        registration = self.node.register_node(
            None, self.consolidate_auth, '', '',
        )
        for addon in self.node.addons:
            callback = addon.after_register
            callback.assert_called_once_with(
                self.node, registration, self.user
            )


class TestProject(OsfTestCase):

    def setUp(self):
        # Create project
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)
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
        assert_equal(api_url, '/api/v1/project/{0}/'.format(self.project._primary_key))

    def test_watch_url(self):
        watch_url = self.project.watch_url
        assert_equal(
            watch_url,
            '/api/v1/project/{0}/watch/'.format(self.project._primary_key)
        )

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
        self.project.add_contributor(contributor=user2, auth=self.consolidate_auth)
        self.project.save()
        assert_in(user2, self.project.contributors)
        assert_equal(self.project.logs[-1].action, 'contributor_added')

    def test_add_unregistered_contributor(self):
        self.project.add_unregistered_contributor(
            email='foo@bar.com',
            fullname='Weezy F. Baby',
            auth=self.consolidate_auth
        )
        self.project.save()
        latest_contributor = self.project.contributors[-1]
        assert_true(isinstance(latest_contributor, User))
        assert_equal(latest_contributor.username, 'foo@bar.com')
        assert_equal(latest_contributor.fullname, 'Weezy F. Baby')
        assert_false(latest_contributor.is_registered)

        # A log event was added
        assert_equal(self.project.logs[-1].action, 'contributor_added')
        assert_in(self.project._primary_key, latest_contributor.unclaimed_records,
            'unclaimed record was added')
        unclaimed_data = latest_contributor.get_unclaimed_record(self.project._primary_key)
        assert_equal(unclaimed_data['referrer_id'],
            self.consolidate_auth.user._primary_key)
        assert_true(self.project.is_contributor(latest_contributor))
        assert_equal(unclaimed_data['email'], 'foo@bar.com')

    def test_add_unregistered_adds_new_unclaimed_record_if_user_already_in_db(self):
        user = UnregUserFactory()
        given_name = fake.name()
        new_user = self.project.add_unregistered_contributor(
            email=user.username,
            fullname=given_name,
            auth=self.consolidate_auth
        )
        self.project.save()
        # new unclaimed record was added
        assert_in(self.project._primary_key, new_user.unclaimed_records)
        unclaimed_data = new_user.get_unclaimed_record(self.project._primary_key)
        assert_equal(unclaimed_data['name'], given_name)

    def test_add_unregistered_raises_error_if_user_is_registered(self):
        user = UserFactory(is_registered=True)  # A registered user
        with assert_raises(ValidationValueError):
            self.project.add_unregistered_contributor(
                email=user.username,
                fullname=user.fullname,
                auth=self.consolidate_auth
            )

    def test_remove_contributor(self):
        # A user is added as a contributor
        user2 = UserFactory()
        self.project.add_contributor(contributor=user2, auth=self.consolidate_auth)
        self.project.save()
        # The user is removed
        self.project.remove_contributor(
            auth=self.consolidate_auth,
            contributor=user2
        )

        self.project.reload()

        assert_not_in(user2, self.project.contributors)
        assert_not_in(user2._id, self.project.permissions)
        assert_equal(self.project.logs[-1].action, 'contributor_removed')

    def test_add_private_link(self):
        link = PrivateLinkFactory()
        link.nodes.append(self.project)
        link.save()
        assert_in(link, self.project.private_links)

    def test_has_anonymous_link(self):
        link1 = PrivateLinkFactory(anonymous=True, key="link1")
        link1.nodes.append(self.project)
        link1.save()
        link2 = PrivateLinkFactory(key="link2")
        link2.nodes.append(self.project)
        link2.save()
        assert_true(has_anonymous_link(self.project, "link1"))
        assert_false(has_anonymous_link(self.project, "link2"))

    def test_remove_unregistered_conributor_removes_unclaimed_record(self):
        new_user = self.project.add_unregistered_contributor(fullname=fake.name(),
            email=fake.email(), auth=Auth(self.project.creator))
        self.project.save()
        assert_true(self.project.is_contributor(new_user))  # sanity check
        assert_in(self.project._primary_key, new_user.unclaimed_records)
        self.project.remove_contributor(
            auth=self.consolidate_auth,
            contributor=new_user
        )
        self.project.save()
        assert_not_in(self.project._primary_key, new_user.unclaimed_records)

    def test_manage_contributors_new_contributor(self):
        user = UserFactory()
        users = [
            {'id': self.project.creator._id, 'permission': 'read', 'visible': True},
            {'id': user._id, 'permission': 'read', 'visible': True},
        ]
        with assert_raises(ValueError):
            self.project.manage_contributors(
                users, auth=self.consolidate_auth, save=True
            )

    def test_manage_contributors_no_contributors(self):
        with assert_raises(ValueError):
            self.project.manage_contributors(
                [], auth=self.consolidate_auth, save=True,
            )

    def test_manage_contributors_no_admins(self):
        user = UserFactory()
        self.project.add_contributor(
            user,
            permissions=['read', 'write', 'admin'],
            save=True
        )
        users = [
            {'id': self.project.creator._id, 'permission': 'read', 'visible': True},
            {'id': user._id, 'permission': 'read', 'visible': True},
        ]
        with assert_raises(ValueError):
            self.project.manage_contributors(
                users, auth=self.consolidate_auth, save=True,
            )

    def test_manage_contributors_no_registered_admins(self):
        unregistered = UnregUserFactory()
        self.project.add_contributor(
            unregistered,
            permissions=['read', 'write', 'admin'],
            save=True
        )
        users = [
            {'id': self.project.creator._id, 'permission': 'read', 'visible': True},
            {'id': unregistered._id, 'permission': 'admin', 'visible': True},
        ]
        with assert_raises(ValueError):
            self.project.manage_contributors(
                users, auth=self.consolidate_auth, save=True,
            )

    def test_set_title(self):
        proj = ProjectFactory(title='That Was Then', creator=self.user)
        proj.set_title('This is now', auth=self.consolidate_auth)
        proj.save()
        # Title was changed
        assert_equal(proj.title, 'This is now')
        # A log event was saved
        latest_log = proj.logs[-1]
        assert_equal(latest_log.action, 'edit_title')
        assert_equal(latest_log.params['title_original'], 'That Was Then')

    def test_contributor_can_edit(self):
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        self.project.add_contributor(
            contributor=contributor, auth=self.consolidate_auth)
        self.project.save()
        assert_true(self.project.can_edit(contributor_auth))
        assert_false(self.project.can_edit(other_guy_auth))

    def test_can_edit_can_be_passed_a_user(self):
        assert_true(self.project.can_edit(user=self.user))

    def test_creator_can_edit(self):
        assert_true(self.project.can_edit(self.consolidate_auth))

    def test_noncontributor_cant_edit_public(self):
        user1 = UserFactory()
        user1_auth = Auth(user=user1)
        # Change project to public
        self.project.set_privacy('public')
        self.project.save()
        # Noncontributor can't edit
        assert_false(self.project.can_edit(user1_auth))

    def test_can_view_private(self):
        # Create contributor and noncontributor
        link = PrivateLinkFactory()
        link.nodes.append(self.project)
        link.save()
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        self.project.add_contributor(
            contributor=contributor, auth=self.consolidate_auth)
        self.project.save()
        # Only creator and contributor can view
        assert_true(self.project.can_view(self.consolidate_auth))
        assert_true(self.project.can_view(contributor_auth))
        assert_false(self.project.can_view(other_guy_auth))
        other_guy_auth.private_key = link.key
        assert_true(self.project.can_view(other_guy_auth))

    def test_creator_cannot_edit_project_if_they_are_removed(self):
        creator = UserFactory()
        project = ProjectFactory(creator=creator)
        contrib = UserFactory()
        project.add_contributor(contrib, auth=Auth(user=creator))
        project.save()
        assert_in(creator, project.contributors)
        # Creator is removed from project
        project.remove_contributor(creator, auth=Auth(user=contrib))
        assert_false(project.can_view(Auth(user=creator)))
        assert_false(project.can_edit(Auth(user=creator)))
        assert_false(project.is_contributor(creator))

    def test_can_view_public(self):
        # Create contributor and noncontributor
        contributor = UserFactory()
        contributor_auth = Auth(user=contributor)
        other_guy = UserFactory()
        other_guy_auth = Auth(user=other_guy)
        self.project.add_contributor(
            contributor=contributor, auth=self.consolidate_auth)
        # Change project to public
        self.project.set_privacy('public')
        self.project.save()
        # Creator, contributor, and noncontributor can view
        assert_true(self.project.can_view(self.consolidate_auth))
        assert_true(self.project.can_view(contributor_auth))
        assert_true(self.project.can_view(other_guy_auth))

    def test_is_contributor(self):
        contributor = UserFactory()
        other_guy = UserFactory()
        self.project.add_contributor(
            contributor=contributor, auth=self.consolidate_auth)
        self.project.save()
        assert_true(self.project.is_contributor(contributor))
        assert_false(self.project.is_contributor(other_guy))
        assert_false(self.project.is_contributor(None))

    def test_is_contributor_unregistered(self):
        unreg = UnregUserFactory()
        self.project.add_unregistered_contributor(
            fullname=fake.name(),
            email=unreg.username,
            auth=self.consolidate_auth
        )
        self.project.save()
        assert_true(self.project.is_contributor(unreg))

    def test_creator_is_contributor(self):
        assert_true(self.project.is_contributor(self.user))
        assert_in(self.user, self.project.contributors)

    def test_cant_add_creator_as_contributor_twice(self):
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
        self.project.add_contributors(
            [
                {'user': user1, 'permissions': ['read', 'write', 'admin'], 'visible': True},
                {'user': user2, 'permissions': ['read', 'write'], 'visible': False}
            ],
            auth=self.consolidate_auth
        )
        self.project.save()
        assert_equal(len(self.project.contributors), 3)
        assert_equal(
            self.project.logs[-1].params['contributors'],
            [user1._id, user2._id]
        )
        assert_in(user1._id, self.project.permissions)
        assert_in(user2._id, self.project.permissions)
        assert_in(user1._id, self.project.visible_contributor_ids)
        assert_not_in(user2._id, self.project.visible_contributor_ids)
        assert_equal(self.project.permissions[user1._id], ['read', 'write', 'admin'])
        assert_equal(self.project.permissions[user2._id], ['read', 'write'])
        assert_equal(
            self.project.logs[-1].params['contributors'],
            [user1._id, user2._id]
        )

    def test_set_privacy(self):
        self.project.set_privacy('public', auth=self.consolidate_auth)
        self.project.save()
        assert_true(self.project.is_public)
        assert_equal(self.project.logs[-1].action, 'made_public')
        self.project.set_privacy('private', auth=self.consolidate_auth)
        self.project.save()
        assert_false(self.project.is_public)
        assert_equal(self.project.logs[-1].action, NodeLog.MADE_PRIVATE)

    def test_set_description(self):
        old_desc = self.project.description
        self.project.set_description(
            'new description', auth=self.consolidate_auth)
        self.project.save()
        assert_equal(self.project.description, 'new description')
        latest_log = self.project.logs[-1]
        assert_equal(latest_log.action, NodeLog.EDITED_DESCRIPTION)
        assert_equal(latest_log.params['description_original'], old_desc)
        assert_equal(latest_log.params['description_new'], 'new description')

    def test_no_parent(self):
        assert_equal(self.project.parent_node, None)

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

    def test_replace_contributor(self):
        contrib = UserFactory()
        self.project.add_contributor(contrib, auth=Auth(self.project.creator))
        self.project.save()
        assert_in(contrib, self.project.contributors)  # sanity check
        replacer = UserFactory()
        old_length = len(self.project.contributors)
        self.project.replace_contributor(contrib, replacer)
        self.project.save()
        new_length = len(self.project.contributors)
        assert_not_in(contrib, self.project.contributors)
        assert_in(replacer, self.project.contributors)
        assert_equal(old_length, new_length)

        # test unclaimed_records is removed
        assert_not_in(
            self.project._primary_key,
            contrib.unclaimed_records.keys()
        )

class TestTemplateNode(OsfTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)

    def _verify_log(self, node):
        """Tests to see that the "created from" log event is present (alone).

        :param node: A node having been created from a template just prior
        """
        assert_equal(len(node.logs), 1)
        assert_equal(node.logs[0].action, NodeLog.CREATED_FROM)

    def test_simple_template(self):
        """Create a templated node, with no changes"""
        # created templated node
        new = self.project.use_as_template(
            auth=self.consolidate_auth
        )

        assert_equal(new.title, self._default_title(self.project))
        assert_not_equal(new.date_created, self.project.date_created)
        self._verify_log(new)

    def test_simple_template_title_changed(self):
        """Create a templated node, with the title changed"""
        changed_title = 'Made from template'

        # create templated node
        new = self.project.use_as_template(
            auth=self.consolidate_auth,
            changes={
                self.project._primary_key: {
                    'title': changed_title,
                }
            }
        )

        assert_equal(new.title, changed_title)
        assert_not_equal(new.date_created, self.project.date_created)
        self._verify_log(new)

    def _create_complex(self):
        # create project connected via Pointer
        self.pointee = ProjectFactory(creator=self.user)
        self.project.add_pointer(self.pointee, auth=self.consolidate_auth)

        # create direct children
        self.component = NodeFactory(creator=self.user, project=self.project)
        self.subproject = ProjectFactory(creator=self.user, project=self.project)

    @staticmethod
    def _default_title(x):
        if isinstance(x, Node):
            return str(language.TEMPLATED_FROM_PREFIX + x.title)
        return str(x.title)


    def test_complex_template(self):
        """Create a templated node from a node with children"""
        self._create_complex()

        # create templated node
        new = self.project.use_as_template(auth=self.consolidate_auth)

        assert_equal(new.title, self._default_title(self.project))
        assert_equal(len(new.nodes), len(self.project.nodes))
        # check that all children were copied
        assert_equal(
            [x.title for x in new.nodes],
            [x.title for x in self.project.nodes],
        )
        # ensure all child nodes were actually copied, instead of moved
        assert {x._primary_key for x in new.nodes}.isdisjoint(
            {x._primary_key for x in self.project.nodes}
        )

    def test_complex_template_titles_changed(self):
        self._create_complex()

        # build changes dict to change each node's title
        changes = {
            x._primary_key: {
                'title': 'New Title ' + str(idx)
            } for idx, x in enumerate(self.project.nodes)
        }

        # create templated node
        new = self.project.use_as_template(
            auth=self.consolidate_auth,
            changes=changes
        )

        for old_node, new_node in zip(self.project.nodes, new.nodes):
            if isinstance(old_node, Node):
                assert_equal(
                    changes[old_node._primary_key]['title'],
                    new_node.title,
                )
            else:
                assert_equal(
                    old_node.title,
                    new_node.title,
                )

    def test_template_files_not_copied(self):
        self.project.add_file(
            self.consolidate_auth, 'test.txt', 'test content', 4, 'text/plain'
        )
        new = self.project.use_as_template(
            auth=self.consolidate_auth
        )
        assert_equal(
            len(self.project.files_current),
            1
        )
        assert_equal(
            len(self.project.files_versions),
            1
        )
        assert_equal(new.files_current, {})
        assert_equal(new.files_versions, {})

    def test_template_wiki_pages_not_copied(self):
        self.project.update_node_wiki(
            'template', 'lol',
            auth=self.consolidate_auth
        )
        new = self.project.use_as_template(
            auth=self.consolidate_auth
        )
        assert_in('template', self.project.wiki_pages_current)
        assert_in('template', self.project.wiki_pages_versions)
        assert_equal(new.wiki_pages_current, {})
        assert_equal(new.wiki_pages_versions, {})

    def test_template_security(self):
        """Create a templated node from a node with public and private children

        Children for which the user has no access should not be copied
        """
        other_user = UserFactory()
        other_user_auth = Auth(user=other_user)

        self._create_complex()

        # set two projects to public - leaving self.component as private
        self.project.is_public = True
        self.project.save()
        self.subproject.is_public = True
        self.subproject.save()

        # add new children, for which the user has each level of access
        self.read = NodeFactory(creator=self.user, project=self.project)
        self.read.add_contributor(other_user, permissions=['read', ])
        self.read.save()

        self.write = NodeFactory(creator=self.user, project=self.project)
        self.write.add_contributor(other_user, permissions=['read', 'write', ])
        self.write.save()

        self.admin = NodeFactory(creator=self.user, project=self.project)
        self.admin.add_contributor(other_user)
        self.admin.save()

        # filter down self.nodes to only include projects the user can see
        visible_nodes = filter(
            lambda x: x.can_view(other_user_auth),
            self.project.nodes
        )

        # create templated node
        new = self.project.use_as_template(auth=other_user_auth)

        assert_equal(new.title, self._default_title(self.project))

        # check that all children were copied
        assert_equal(
            set(x.template_node._id for x in new.nodes),
            set(x._id for x in visible_nodes),
        )
        # ensure all child nodes were actually copied, instead of moved
        assert_true({x._primary_key for x in new.nodes}.isdisjoint(
            {x._primary_key for x in self.project.nodes}
        ))

        # ensure that the creator is admin for each node copied
        for node in new.nodes:
            assert_equal(
                node.permissions.get(other_user._id),
                ['read', 'write', 'admin'],
            )


class TestForkNode(OsfTestCase):
    def setUp(self):
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)
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
        assert_equal(original.parent_node is None, fork.parent_node is None)

        # Test modified fields
        assert_true(fork.is_fork)
        assert_equal(len(fork.private_links), 0)
        assert_equal(fork.forked_from, original)
        assert_in(fork._id, original.fork_list)
        assert_in(fork._id, original.node__forked)
        # Note: Must cast ForeignList to list for comparison
        assert_equal(list(fork.contributors), [fork_user])
        assert_true((fork_date - fork.date_created) < datetime.timedelta(seconds=30))
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

        # Test that pointers were copied correctly
        assert_equal(
            [pointer.node for pointer in original.nodes_pointer],
            [pointer.node for pointer in fork.nodes_pointer],
        )

        # Test that add-ons were copied correctly
        assert_equal(
            original.get_addon_names(),
            fork.get_addon_names()
        )
        assert_equal(
            [addon.config.short_name for addon in original.get_addons()],
            [addon.config.short_name for addon in fork.get_addons()]
        )

        fork_user_auth = Auth(user=fork_user)
        # Recursively compare children
        for idx, child in enumerate(original.nodes):
            if child.can_view(fork_user_auth):
                self._cmp_fork_original(fork_user, fork_date, fork.nodes[idx],
                                        child, title_prepend='')

    @mock.patch('framework.status.push_status_message')
    def test_fork_recursion(self, mock_push_status_message):
        """Omnibus test for forking.

        """
        # Make some children
        self.component = NodeFactory(creator=self.user, project=self.project)
        self.subproject = ProjectFactory(creator=self.user, project=self.project)

        # Add files to test copying
        self.project.add_file(
            self.consolidate_auth, 'test.txt', 'test content', 4, 'text/plain'
        )
        self.component.add_file(
            self.consolidate_auth, 'test2.txt', 'test content2', 4, 'text/plain'
        )
        self.subproject.add_file(
            self.consolidate_auth, 'test3.txt', 'test content3', 4, 'text/plain'
        )

        # Add pointers to test copying
        pointee = ProjectFactory()
        self.project.add_pointer(pointee, auth=self.consolidate_auth)
        self.component.add_pointer(pointee, auth=self.consolidate_auth)
        self.subproject.add_pointer(pointee, auth=self.consolidate_auth)

        # Add add-on to test copying
        self.project.add_addon('github', self.consolidate_auth)
        self.component.add_addon('github', self.consolidate_auth)
        self.subproject.add_addon('github', self.consolidate_auth)

        # Log time
        fork_date = datetime.datetime.utcnow()

        # Fork node
        fork = self.project.fork_node(auth=self.consolidate_auth)

        # Compare fork to original
        self._cmp_fork_original(self.user, fork_date, fork, self.project)

    def test_fork_private_children(self):
        """Tests that only public components are created

        """
        # Make project public
        self.project.set_privacy('public')
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
        user2 = UserFactory()
        user2_auth = Auth(user=user2)
        # New user forks the project
        fork = self.project.fork_node(user2_auth)

        # fork correct children
        assert_equal(len(fork.nodes), 2)
        assert_not_in('Not Forked', [node.title for node in fork.nodes])

    def test_fork_not_public(self):
        self.project.set_privacy('public')
        fork = self.project.fork_node(self.consolidate_auth)
        assert_false(fork.is_public)

    def test_not_fork_private_link(self):
        link = PrivateLinkFactory()
        link.nodes.append(self.project)
        link.save()
        fork = self.project.fork_node(self.consolidate_auth)
        assert_not_in(link, fork.private_links)

    def test_cannot_fork_private_node(self):
        user2 = UserFactory()
        user2_auth = Auth(user=user2)
        fork = self.project.fork_node(user2_auth)
        assert_false(fork)

    def test_can_fork_public_node(self):
        self.project.set_privacy('public')
        user2 = UserFactory()
        user2_auth = Auth(user=user2)
        fork = self.project.fork_node(user2_auth)
        assert_true(fork)

    def test_contributor_can_fork(self):
        user2 = UserFactory()
        self.project.add_contributor(user2)
        user2_auth = Auth(user=user2)
        fork = self.project.fork_node(user2_auth)
        assert_true(fork)

    def test_fork_registration(self):
        self.registration = RegistrationFactory(project=self.project)
        fork = self.registration.fork_node(self.consolidate_auth)

        # fork should not be a registration
        assert_false(fork.is_registration)

        # Compare fork to original
        self._cmp_fork_original(self.user,
                                datetime.datetime.utcnow(),
                                fork,
                                self.registration)


class TestRegisterNode(OsfTestCase):

    def setUp(self):
        ensure_schemas()
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        self.link = PrivateLinkFactory()
        self.link.nodes.append(self.project)
        self.link.save()
        self.registration = RegistrationFactory(project=self.project)

    def test_factory(self):
        # Create a registration with kwargs
        registration1 = RegistrationFactory(
            title='t1', description='d1', creator=self.user,
        )
        assert_equal(registration1.title, 't1')
        assert_equal(registration1.description, 'd1')
        assert_equal(len(registration1.contributors), 1)
        assert_in(self.user, registration1.contributors)
        assert_equal(registration1.registered_user, self.user)
        assert_equal(len(registration1.registered_meta), 1)
        assert_equal(len(registration1.private_links), 0)


        # Create a registration from a project
        user2 = UserFactory()
        self.project.add_contributor(user2)
        registration2 = RegistrationFactory(
            project=self.project,
            user=user2,
            template='Template2',
            data='Something else',
        )
        assert_equal(registration2.registered_from, self.project)
        assert_equal(registration2.registered_user, user2)
        assert_equal(registration2.registered_meta['Template2'], 'Something else')

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
        self.project.set_privacy('public')
        registration = RegistrationFactory(project=self.project)
        assert_true(registration.is_public)

    def test_contributors(self):
        assert_equal(self.registration.contributors, self.project.contributors)

    def test_forked_from(self):
        # A a node that is not a fork
        assert_equal(self.registration.forked_from, None)
        # A node that is a fork
        fork = self.project.fork_node(self.consolidate_auth)
        registration = RegistrationFactory(project=fork)
        assert_equal(registration.forked_from, self.project)

    def test_private_links(self):
        assert_not_equal(
            self.registration.private_links,
            self.project.private_links
        )

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

        # Reload the registration; else test won't catch failures to save
        registration.reload()

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
            delta=datetime.timedelta(seconds=30),
        )

    def test_registered_addons(self):
        assert_equal(
            [addon.config.short_name for addon in self.registration.get_addons()],
            [addon.config.short_name for addon in self.registration.registered_from.get_addons()],
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


class TestNodeLog(OsfTestCase):

    def setUp(self):
        self.log = NodeLogFactory()

    def test_node_log_factory(self):
        log = NodeLogFactory()
        assert_true(log.action)

    def test_serialize(self):
        node = NodeFactory(category='hypothesis')
        log = NodeLogFactory(params={'node': node._primary_key})
        node.logs.append(log)
        node.save()
        d = log.serialize()
        assert_equal(d['action'], log.action)
        assert_equal(d['node']['node_type'], 'component')
        assert_equal(d['node']['category'], 'Hypothesis')

        assert_equal(d['node']['url'], log.node.url)
        assert_equal(d['date'], utils.rfcformat(log.date))
        assert_in('contributors', d)
        assert_equal(d['user']['fullname'], log.user.fullname)
        assert_equal(d['user']['url'], log.user.url)
        assert_in('api_key', d)
        assert_equal(d['params'], log.params)
        assert_equal(d['node']['title'], log.node.title)

    def test_render_log_contributor_unregistered(self):
        node = NodeFactory()
        name, email = fake.name(), fake.email()
        unreg = node.add_unregistered_contributor(fullname=name, email=email,
            auth=Auth(node.creator))
        node.save()

        log = NodeLogFactory(params={'node': node._primary_key})
        ret = log._render_log_contributor(unreg._primary_key)

        assert_false(ret['registered'])
        record = unreg.get_unclaimed_record(node._primary_key)
        assert_equal(ret['fullname'], record['name'])

    def test_render_log_contributor_none(self):
        log = NodeLogFactory()
        assert_equal(log._render_log_contributor(None), None)

    def test_tz_date(self):
        assert_equal(self.log.tz_date.tzinfo, pytz.UTC)

    def test_formatted_date(self):
        iso_formatted = self.log.formatted_date  # The string version in iso format
        # Reparse the date
        parsed = parser.parse(iso_formatted)
        assert_equal(parsed, self.log.tz_date)


class TestPermissions(OsfTestCase):

    def setUp(self):
        self.project = ProjectFactory()

    def test_default_creator_permissions(self):
        assert_equal(
            set(CREATOR_PERMISSIONS),
            set(self.project.permissions[self.project.creator._id])
        )

    def test_default_contributor_permissions(self):
        user = UserFactory()
        self.project.add_contributor(user, permissions=['read'], auth=Auth(user=self.project.creator))
        self.project.save()
        assert_equal(
            set(['read']),
            set(self.project.get_permissions(user))
        )

    def test_adjust_permissions(self):
        self.project.permissions[42] = ['dance']
        self.project.save()
        assert_not_in(42, self.project.permissions)

    def test_add_permission(self):
        self.project.add_permission(self.project.creator, 'dance')
        assert_in(self.project.creator._id, self.project.permissions)
        assert_in('dance', self.project.permissions[self.project.creator._id])

    def test_add_permission_already_granted(self):
        self.project.add_permission(self.project.creator, 'dance')
        with assert_raises(ValueError):
            self.project.add_permission(self.project.creator, 'dance')

    def test_remove_permission(self):
        self.project.add_permission(self.project.creator, 'dance')
        self.project.remove_permission(self.project.creator, 'dance')
        assert_not_in('dance', self.project.permissions[self.project.creator._id])

    def test_remove_permission_not_granted(self):
        with assert_raises(ValueError):
            self.project.remove_permission(self.project.creator, 'dance')

    def test_has_permission_true(self):
        self.project.add_permission(self.project.creator, 'dance')
        assert_true(self.project.has_permission(self.project.creator, 'dance'))

    def test_has_permission_false(self):
        self.project.add_permission(self.project.creator, 'dance')
        assert_false(self.project.has_permission(self.project.creator, 'sing'))

    def test_has_permission_not_in_dict(self):
        assert_false(self.project.has_permission(self.project.creator, 'dance'))


class TestPointer(OsfTestCase):

    def setUp(self):
        self.pointer = PointerFactory()

    def test_title(self):
        assert_equal(
            self.pointer.title,
            self.pointer.node.title
        )

    def test_contributors(self):
        assert_equal(
            self.pointer.contributors,
            self.pointer.node.contributors
        )

    def _assert_clone(self, pointer, cloned):
        assert_not_equal(
            pointer._id,
            cloned._id
        )
        assert_equal(
            pointer.node,
            cloned.node
        )

    def test_clone(self):
        cloned = self.pointer._clone()
        self._assert_clone(self.pointer, cloned)

    def test_clone_no_node(self):
        pointer = Pointer()
        cloned = pointer._clone()
        assert_equal(cloned, None)

    def test_fork(self):
        forked = self.pointer.fork_node()
        self._assert_clone(self.pointer, forked)

    def test_register(self):
        registered = self.pointer.fork_node()
        self._assert_clone(self.pointer, registered)

    def test_register_with_pointer_to_registration(self):
        """Check for regression"""
        pointee = RegistrationFactory()
        project = ProjectFactory()
        auth = Auth(user=project.creator)
        project.add_pointer(pointee, auth=auth)
        registration = project.register_node(None, auth, '', '')
        assert_equal(registration.nodes[0].node, pointee)

    def test_has_pointers_recursive_false(self):
        project = ProjectFactory()
        node = NodeFactory(project=project)
        assert_false(project.has_pointers_recursive)
        assert_false(node.has_pointers_recursive)

    def test_has_pointers_recursive_true(self):
        project = ProjectFactory()
        node = NodeFactory(project=project)
        node.nodes.append(self.pointer)
        assert_true(node.has_pointers_recursive)
        assert_true(project.has_pointers_recursive)


class TestWatchConfig(OsfTestCase):

    def test_factory(self):
        config = WatchConfigFactory(digest=True, immediate=False)
        assert_true(config.digest)
        assert_false(config.immediate)
        assert_true(config.node._id)


class TestUnregisteredUser(OsfTestCase):

    def setUp(self):
        self.referrer = UserFactory()
        self.project = ProjectFactory(creator=self.referrer)
        self.user = UnregUserFactory()

    def add_unclaimed_record(self):
        given_name = 'Fredd Merkury'
        email = fake.email()
        self.user.add_unclaimed_record(node=self.project,
            given_name=given_name, referrer=self.referrer,
            email=email)
        self.user.save()
        data = self.user.unclaimed_records[self.project._primary_key]
        return email, data

    def test_unregistered_factory(self):
        u1 = UnregUserFactory()
        assert_false(u1.is_registered)
        assert_true(u1.password is None)
        assert_true(u1.fullname)

    def test_unconfirmed_factory(self):
        u = UnconfirmedUserFactory()
        assert_false(u.is_registered)
        assert_true(u.username)
        assert_true(u.fullname)
        assert_true(u.password)
        assert_equal(len(u.email_verifications.keys()), 1)

    def test_add_unclaimed_record(self):
        email, data = self.add_unclaimed_record()
        assert_equal(data['name'], 'Fredd Merkury')
        assert_equal(data['referrer_id'], self.referrer._primary_key)
        assert_in('token', data)
        assert_equal(data['email'], email)
        assert_equal(data, self.user.get_unclaimed_record(self.project._primary_key))

    def test_get_claim_url(self):
        self.add_unclaimed_record()
        uid = self.user._primary_key
        pid = self.project._primary_key
        token = self.user.get_unclaimed_record(pid)['token']
        domain = settings.DOMAIN
        assert_equal(self.user.get_claim_url(pid, external=True),
            '{domain}user/{uid}/{pid}/claim/?token={token}'.format(**locals()))

    def test_get_claim_url_raises_value_error_if_not_valid_pid(self):
        with assert_raises(ValueError):
            self.user.get_claim_url('invalidinput')

    def test_cant_add_unclaimed_record_if_referrer_isnt_contributor(self):
        project = ProjectFactory()  # referrer isn't a contributor to this project
        with assert_raises(PermissionsError):
            self.user.add_unclaimed_record(node=project,
                given_name='fred m', referrer=self.referrer)

    def test_register(self):
        assert_false(self.user.is_registered)  # sanity check
        assert_false(self.user.is_claimed)
        email = fake.email()
        self.user.register(username=email, password='killerqueen')
        self.user.save()
        assert_true(self.user.is_claimed)
        assert_true(self.user.is_registered)
        assert_true(self.user.check_password('killerqueen'))
        assert_equal(self.user.username, email)

    def test_registering_with_a_different_email_adds_to_emails_list(self):
        user = UnregUserFactory()
        assert_equal(user.password, None)  # sanity check
        user.register(username=fake.email(), password='killerqueen')

    def test_verify_claim_token(self):
        self.add_unclaimed_record()
        valid = self.user.get_unclaimed_record(self.project._primary_key)['token']
        assert_true(self.user.verify_claim_token(valid, project_id=self.project._primary_key))
        assert_false(self.user.verify_claim_token('invalidtoken', project_id=self.project._primary_key))

    def test_claim_contributor(self):
        self.add_unclaimed_record()
        # sanity cheque
        assert_false(self.user.is_registered)
        assert_true(self.project)


class TestTags(OsfTestCase):

    def setUp(self):
        super(TestTags, self).setUp()
        self.project = ProjectFactory()
        self.auth = Auth(self.project.creator)

    def test_add_tag(self):
        self.project.add_tag('scientific', auth=self.auth)
        assert_in('scientific', self.project.tags)
        assert_equal(
            self.project.logs[-1].action,
            NodeLog.TAG_ADDED
        )

    def test_add_tag_too_long(self):
        with assert_raises(ValidationError):
            self.project.add_tag('q' * 129, auth=self.auth)

    def test_remove_tag(self):
        self.project.add_tag('scientific', auth=self.auth)
        self.project.remove_tag('scientific', auth=self.auth)
        assert_not_in('scientific', self.project.tags)
        assert_equal(
            self.project.logs[-1].action,
            NodeLog.TAG_REMOVED
        )

    def test_remove_tag_not_present(self):
        self.project.remove_tag('scientific', auth=self.auth)
        assert_equal(
            self.project.logs[-1].action,
            NodeLog.PROJECT_CREATED
        )


class TestContributorVisibility(OsfTestCase):

    def setUp(self):
        super(TestContributorVisibility, self).setUp()
        self.project = ProjectFactory()
        self.user2 = UserFactory()
        self.project.add_contributor(self.user2)

    def test_get_visible_true(self):
        assert_true(self.project.get_visible(self.project.creator))

    def test_get_visible_false(self):
        self.project.set_visible(self.project.creator, False)
        assert_false(self.project.get_visible(self.project.creator))

    def test_make_invisible(self):
        self.project.set_visible(self.project.creator, False, save=True)
        self.project.reload()
        assert_not_in(
            self.project.creator._id,
            self.project.visible_contributor_ids
        )
        assert_not_in(
            self.project.creator,
            self.project.visible_contributors
        )
        assert_equal(
            self.project.logs[-1].action,
            NodeLog.MADE_CONTRIBUTOR_INVISIBLE
        )

    def test_make_visible(self):
        self.project.set_visible(self.project.creator, False, save=True)
        self.project.set_visible(self.project.creator, True, save=True)
        self.project.reload()
        assert_in(
            self.project.creator._id,
            self.project.visible_contributor_ids
        )
        assert_in(
            self.project.creator,
            self.project.visible_contributors
        )
        assert_equal(
            self.project.logs[-1].action,
            NodeLog.MADE_CONTRIBUTOR_VISIBLE
        )
        # Regression test: Ensure that hiding and showing the first contributor
        # does not change the visible contributor order
        assert_equal(
            self.project.visible_contributors,
            [self.project.creator, self.user2]
        )

    def test_set_visible_missing(self):
        with assert_raises(ValueError):
            self.project.set_visible(UserFactory(), True)


class TestProjectWithAddons(OsfTestCase):

    def test_factory(self):
        p = ProjectWithAddonFactory(addon='s3')
        assert_true(p.get_addon('s3'))
        assert_true(p.creator.get_addon('s3'))


class TestComments(OsfTestCase):

    def setUp(self):
        self.comment = CommentFactory()
        self.consolidated_auth = Auth(user=self.comment.user)

    def test_create(self):
        comment = Comment.create(
            auth=self.consolidated_auth,
            user=self.comment.user,
            node=self.comment.node,
            target=self.comment.target,
            is_public=True,
        )
        assert_equal(comment.user, self.comment.user)
        assert_equal(comment.node, self.comment.node)
        assert_equal(comment.target, self.comment.target)
        assert_equal(len(comment.node.logs), 2)
        assert_equal(comment.node.logs[-1].action, NodeLog.COMMENT_ADDED)

    def test_edit(self):
        self.comment.edit(
            auth=self.consolidated_auth,
            content='edited'
        )
        assert_equal(self.comment.content, 'edited')
        assert_true(self.comment.modified)
        assert_equal(len(self.comment.node.logs), 2)
        assert_equal(self.comment.node.logs[-1].action, NodeLog.COMMENT_UPDATED)

    def test_delete(self):
        self.comment.delete(auth=self.consolidated_auth)
        assert_equal(self.comment.is_deleted, True)
        assert_equal(len(self.comment.node.logs), 2)
        assert_equal(self.comment.node.logs[-1].action, NodeLog.COMMENT_REMOVED)

    def test_undelete(self):
        self.comment.delete(auth=self.consolidated_auth)
        self.comment.undelete(auth=self.consolidated_auth)
        assert_equal(self.comment.is_deleted, False)
        assert_equal(len(self.comment.node.logs), 3)
        assert_equal(self.comment.node.logs[-1].action, NodeLog.COMMENT_ADDED)

    def test_report_abuse(self):
        user = UserFactory()
        self.comment.report_abuse(user, category='spam', text='ads', save=True)
        assert_in(user._id, self.comment.reports)
        assert_equal(
            self.comment.reports[user._id],
            {'category': 'spam', 'text': 'ads'}
        )

    def test_report_abuse_own_comment(self):
        with assert_raises(ValueError):
            self.comment.report_abuse(
                self.comment.user, category='spam', text='ads', save=True
            )

    def test_unreport_abuse(self):
        user = UserFactory()
        self.comment.report_abuse(user, category='spam', text='ads', save=True)
        self.comment.unreport_abuse(user, save=True)
        assert_not_in(user._id, self.comment.reports)

    def test_unreport_abuse_not_reporter(self):
        reporter = UserFactory()
        non_reporter = UserFactory()
        self.comment.report_abuse(reporter, category='spam', text='ads', save=True)
        with assert_raises(ValueError):
            self.comment.unreport_abuse(non_reporter, save=True)
        assert_in(reporter._id, self.comment.reports)

    def test_validate_reports_bad_key(self):
        self.comment.reports[None] = {'category': 'spam', 'text': 'ads'}
        with assert_raises(ValidationValueError):
            self.comment.save()

    def test_validate_reports_bad_type(self):
        self.comment.reports[self.comment.user._id] = 'not a dict'
        with assert_raises(ValidationTypeError):
            self.comment.save()

    def test_validate_reports_bad_value(self):
        self.comment.reports[self.comment.user._id] = {'foo': 'bar'}
        with assert_raises(ValidationValueError):
            self.comment.save()


if __name__ == '__main__':
    unittest.main()
