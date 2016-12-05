# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa (PEP8 asserts)
import mock
import urlparse
from modularodm import Q
from modularodm.exceptions import NoResultsFound, ValidationValueError

from framework.celery_tasks import handlers
from website.addons.osfstorage import settings as osfstorage_settings
from website.files.models.osfstorage import OsfStorageFile
from website.preprints.tasks import format_preprint
from website.util import permissions

from framework.auth import Auth
from framework.exceptions import PermissionsError

from website import settings
from website.project.model import (
    NodeLog,
    NodeStateError
)

from tests.base import OsfTestCase
from tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    PreprintFactory,
    PreprintProviderFactory,
    SubjectFactory
)
from tests.utils import assert_logs, assert_not_logs


class TestPreprintFactory(OsfTestCase):
    def setUp(self):
        super(TestPreprintFactory, self).setUp()

        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.preprint = PreprintFactory(creator=self.user)
        self.preprint.save()

    def test_is_preprint(self):
        assert_true(self.preprint.node.is_preprint)

    def test_preprint_is_public(self):
        assert_true(self.preprint.node.is_public)


class TestSetPreprintFile(OsfTestCase):

    def setUp(self):
        super(TestSetPreprintFile, self).setUp()

        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.read_write_user = AuthUserFactory()
        self.read_write_user_auth = Auth(user=self.read_write_user)

        self.project = ProjectFactory(creator=self.user)
        self.file = OsfStorageFile.create(
            is_file=True,
            node=self.project,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        self.file.save()

        self.file_two = OsfStorageFile.create(
            is_file=True,
            node=self.project,
            path='/pandapanda.txt',
            name='pandapanda.txt',
            materialized_path='/pandapanda.txt')
        self.file_two.save()

        self.project.add_contributor(self.read_write_user, permissions=[permissions.WRITE])
        self.project.save()

        self.preprint = PreprintFactory(project=self.project, finish=False)

    @assert_logs(NodeLog.MADE_PUBLIC, 'project')
    @assert_logs(NodeLog.PREPRINT_INITIATED, 'project', -2)
    def test_is_preprint_property_new_file_to_published(self):
        assert_false(self.project.is_preprint)
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        self.project.reload()
        assert_false(self.project.is_preprint)
        with assert_raises(ValueError):
            self.preprint.set_published(True, auth=self.auth, save=True)
        self.preprint.provider = PreprintProviderFactory()
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=self.auth, save=True)
        self.project.reload()
        assert_false(self.project.is_preprint)
        self.preprint.set_published(True, auth=self.auth, save=True)
        self.project.reload()
        assert_true(self.project.is_preprint)


    def test_project_made_public(self):
        assert_false(self.project.is_public)
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_false(self.project.is_public)
        with assert_raises(ValueError):
            self.preprint.set_published(True, auth=self.auth, save=True)
        self.preprint.provider = PreprintProviderFactory()
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=self.auth, save=True)
        self.project.reload()
        assert_false(self.project.is_public)
        self.preprint.set_published(True, auth=self.auth, save=True)
        self.project.reload()
        assert_true(self.project.is_public)

    def test_add_primary_file(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file, self.file)
        assert_equal(type(self.project.preprint_file), type(self.file.stored_object))

    @assert_logs(NodeLog.PREPRINT_FILE_UPDATED, 'project')
    def test_change_primary_file(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file, self.file)

        self.preprint.set_primary_file(self.file_two, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file_two._id)

    def test_add_invalid_file(self):
        with assert_raises(AttributeError):
            self.preprint.set_primary_file('inatlanta', auth=self.auth, save=True)

    def test_preprint_created_date(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)

        assert(self.preprint.date_created)
        assert_not_equal(self.project.date_created, self.preprint.date_created)

    def test_non_admin_update_file(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)

        with assert_raises(PermissionsError):
            self.preprint.set_primary_file(self.file_two, auth=self.read_write_user_auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)


class TestPreprintServicePermissions(OsfTestCase):
    def setUp(self):
        super(TestPreprintServicePermissions, self).setUp()
        self.user = AuthUserFactory()
        self.write_contrib = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_contributor(self.write_contrib, permissions=[permissions.WRITE])

        self.preprint = PreprintFactory(project=self.project, is_published=False)


    def test_nonadmin_cannot_set_subjects(self):
        initial_subjects = self.preprint.subjects
        with assert_raises(PermissionsError):
            self.preprint.set_subjects([[SubjectFactory()._id]], auth=Auth(self.write_contrib), save=True)

        self.preprint.reload()
        assert_equal(initial_subjects, self.preprint.subjects)

    def test_nonadmin_cannot_set_file(self):
        initial_file = self.preprint.primary_file
        file = OsfStorageFile.create(
            is_file=True,
            node=self.project,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        file.save()
        
        with assert_raises(PermissionsError):
            self.preprint.set_primary_file(file, auth=Auth(self.write_contrib), save=True)

        self.preprint.reload()
        self.preprint.node.reload()
        assert_equal(initial_file._id, self.preprint.primary_file._id)

    def test_nonadmin_cannot_publish(self):
        assert_false(self.preprint.is_published)

        with assert_raises(PermissionsError):
            self.preprint.set_published(True, auth=Auth(self.write_contrib), save=True)

        assert_false(self.preprint.is_published)

    def test_admin_can_set_subjects(self):
        initial_subjects = self.preprint.subjects
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=Auth(self.user), save=True)

        self.preprint.reload()
        assert_not_equal(initial_subjects, self.preprint.subjects)

    def test_admin_can_set_file(self):
        initial_file = self.preprint.primary_file
        file = OsfStorageFile.create(
            is_file=True,
            node=self.project,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        file.save()
        
        self.preprint.set_primary_file(file, auth=Auth(self.user), save=True)

        self.preprint.reload()
        self.preprint.node.reload()
        assert_not_equal(initial_file._id, self.preprint.primary_file._id)
        assert_equal(file._id, self.preprint.primary_file._id)

    def test_admin_can_publish(self):
        assert_false(self.preprint.is_published)

        self.preprint.set_published(True, auth=Auth(self.user), save=True)

        assert_true(self.preprint.is_published)

    def test_admin_cannot_unpublish(self):
        assert_false(self.preprint.is_published)

        self.preprint.set_published(True, auth=Auth(self.user), save=True)

        assert_true(self.preprint.is_published)

        with assert_raises(ValueError) as e:
            self.preprint.set_published(False, auth=Auth(self.user), save=True)

        assert_in('Cannot unpublish', e.exception.message)


class TestPreprintProviders(OsfTestCase):
    def setUp(self):
        super(TestPreprintProviders, self).setUp()
        self.preprint = PreprintFactory(providers=[])
        self.provider = PreprintProviderFactory(name='WWEArxiv')

    def test_add_provider(self):
        assert_not_equal(self.preprint.provider, self.provider)

        self.preprint.provider = self.provider
        self.preprint.save()
        self.preprint.reload()

        assert_equal(self.preprint.provider, self.provider)

    def test_remove_provider(self):
        self.preprint.provider = None
        self.preprint.save()
        self.preprint.reload()

        assert_equal(self.preprint.provider, None)

class TestOnPreprintUpdatedTask(OsfTestCase):
    def setUp(self):
        super(TestOnPreprintUpdatedTask, self).setUp()
        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.preprint = PreprintFactory()

        self.preprint.node.add_tag('preprint', self.auth, save=False)
        self.preprint.node.add_tag('spoderman', self.auth, save=False)
        self.preprint.node.add_unregistered_contributor('BoJack Horseman', 'horse@man.org', Auth(self.preprint.node.creator))
        self.preprint.node.add_contributor(self.user, visible=False)
        self.preprint.node.save()

        self.preprint.node.creator.given_name = 'ZZYZ'
        self.preprint.node.creator.save()

        self.preprint.set_subjects([[SubjectFactory()._id]], auth=Auth(self.preprint.node.creator), save=False)

    def tearDown(self):
        handlers.celery_before_request()
        super(TestOnPreprintUpdatedTask, self).tearDown()

    def test_format_preprint(self):
        res = format_preprint(self.preprint)

        assert set(gn['@type'] for gn in res) == {'creator', 'contributor', 'throughsubjects', 'subject', 'throughtags', 'tag', 'workidentifier', 'agentidentifier', 'person', 'preprint'}

        nodes = dict(enumerate(res))
        preprint = nodes.pop(next(k for k, v in nodes.items() if v['@type'] == 'preprint'))
        assert preprint['title'] == self.preprint.node.title
        assert preprint['description'] == self.preprint.node.description
        assert preprint['is_deleted'] == (not self.preprint.is_published or not self.preprint.node.is_public or self.preprint.node.is_preprint_orphan)
        assert preprint['date_updated'] == self.preprint.date_modified.isoformat()
        assert preprint['date_published'] == self.preprint.date_published.isoformat()

        tags = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'tag']
        through_tags = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'throughtags']
        assert sorted(tag['@id'] for tag in tags) == sorted(tt['tag']['@id'] for tt in through_tags)
        assert sorted(tag['name'] for tag in tags) == ['preprint', 'spoderman']

        subjects = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'subject']
        through_subjects = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'throughsubjects']
        assert sorted(subject['@id'] for subject in subjects) == sorted(tt['subject']['@id'] for tt in through_subjects)
        assert sorted(subject['name'] for subject in subjects) == ['Example Subject #1']

        people = sorted([nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'person'], key=lambda x: x['given_name'])
        assert people == [{
            '@id': people[0]['@id'],
            '@type': 'person',
            'given_name': u'BoJack',
            'family_name': u'Horseman',
        }, {
            '@id': people[1]['@id'],
            '@type': 'person',
            'given_name': self.user.given_name,
            'family_name': self.user.family_name,
        }, {
            '@id': people[2]['@id'],
            '@type': 'person',
            'given_name': self.preprint.node.creator.given_name,
            'family_name': self.preprint.node.creator.family_name,
        }]

        creators = sorted([nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'creator'], key=lambda x: x['order_cited'])
        assert creators == [{
            '@id': creators[0]['@id'],
            '@type': 'creator',
            'order_cited': 0,
            'cited_as': self.preprint.node.creator.fullname,
            'agent': {'@id': people[2]['@id'], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }, {
            '@id': creators[1]['@id'],
            '@type': 'creator',
            'order_cited': 1,
            'cited_as': 'BoJack Horseman',
            'agent': {'@id': people[0]['@id'], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }]

        contributors = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'contributor']
        assert contributors == [{
            '@id': contributors[0]['@id'],
            '@type': 'contributor',
            'cited_as': self.user.fullname,
            'agent': {'@id': people[1]['@id'], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }]

        agentidentifiers = {nodes.pop(k)['uri'] for k, v in nodes.items() if v['@type'] == 'agentidentifier'}
        assert agentidentifiers == set([
            'mailto:' + self.user.username,
            'mailto:' + self.preprint.node.creator.username,
            self.user.profile_image_url(),
            self.preprint.node.creator.profile_image_url(),
        ]) | set(urlparse.urljoin(settings.DOMAIN, user.profile_url) for user in self.preprint.node.contributors if user.is_registered)

        workidentifiers = {nodes.pop(k)['uri'] for k, v in nodes.items() if v['@type'] == 'workidentifier'}
        assert workidentifiers == set([
            'http://dx.doi.org/{}'.format(self.preprint.article_doi),
            urlparse.urljoin(settings.DOMAIN, self.preprint.url)
        ])

        assert nodes == {}

    def test_format_preprint_nones(self):
        self.preprint.node.tags = None
        self.preprint.date_published = None
        self.preprint.set_subjects([], auth=Auth(self.preprint.node.creator), save=False)

        res = format_preprint(self.preprint)

        assert set(gn['@type'] for gn in res) == {'creator', 'contributor', 'workidentifier', 'agentidentifier', 'person', 'preprint'}

        nodes = dict(enumerate(res))
        preprint = nodes.pop(next(k for k, v in nodes.items() if v['@type'] == 'preprint'))
        assert preprint['title'] == self.preprint.node.title
        assert preprint['description'] == self.preprint.node.description
        assert preprint['is_deleted'] == (not self.preprint.is_published or not self.preprint.node.is_public or self.preprint.node.is_preprint_orphan)
        assert preprint['date_updated'] == self.preprint.date_modified.isoformat()
        assert preprint.get('date_published') is None

        people = sorted([nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'person'], key=lambda x: x['given_name'])
        assert people == [{
            '@id': people[0]['@id'],
            '@type': 'person',
            'given_name': u'BoJack',
            'family_name': u'Horseman',
        }, {
            '@id': people[1]['@id'],
            '@type': 'person',
            'given_name': self.user.given_name,
            'family_name': self.user.family_name,
        }, {
            '@id': people[2]['@id'],
            '@type': 'person',
            'given_name': self.preprint.node.creator.given_name,
            'family_name': self.preprint.node.creator.family_name,
        }]

        creators = sorted([nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'creator'], key=lambda x: x['order_cited'])
        assert creators == [{
            '@id': creators[0]['@id'],
            '@type': 'creator',
            'order_cited': 0,
            'cited_as': self.preprint.node.creator.fullname,
            'agent': {'@id': people[2]['@id'], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }, {
            '@id': creators[1]['@id'],
            '@type': 'creator',
            'order_cited': 1,
            'cited_as': 'BoJack Horseman',
            'agent': {'@id': people[0]['@id'], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }]

        contributors = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'contributor']
        assert contributors == [{
            '@id': contributors[0]['@id'],
            '@type': 'contributor',
            'cited_as': self.user.fullname,
            'agent': {'@id': people[1]['@id'], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }]

        agentidentifiers = {nodes.pop(k)['uri'] for k, v in nodes.items() if v['@type'] == 'agentidentifier'}
        assert agentidentifiers == set([
            'mailto:' + self.user.username,
            'mailto:' + self.preprint.node.creator.username,
            self.user.profile_image_url(),
            self.preprint.node.creator.profile_image_url(),
        ]) | set(urlparse.urljoin(settings.DOMAIN, user.profile_url) for user in self.preprint.node.contributors if user.is_registered)

        workidentifiers = {nodes.pop(k)['uri'] for k, v in nodes.items() if v['@type'] == 'workidentifier'}
        assert workidentifiers == set([
            'http://dx.doi.org/{}'.format(self.preprint.article_doi),
            urlparse.urljoin(settings.DOMAIN, self.preprint.url)
        ])

        assert nodes == {}
