# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa (PEP8 asserts)
import mock
import urlparse
import pytest

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from addons.osfstorage.models import OsfStorageFile
from api_tests import utils as api_test_utils
from framework.auth import Auth
from framework.celery_tasks import handlers
from framework.postcommit_tasks.handlers import enqueue_postcommit_task, get_task_from_postcommit_queue
from framework.exceptions import PermissionsError
from osf.models import NodeLog, Subject
from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
    PreprintProviderFactory,
    ProjectFactory,
    SubjectFactory,
    UserFactory,
    PreprintRequestFactory,
)
from osf_tests.utils import MockShareResponse
from osf.utils import permissions
from osf.utils.workflows import DefaultStates, RequestTypes
from tests.utils import assert_logs
from tests.base import OsfTestCase
from website import settings, mails
from website.identifiers.clients import CrossRefClient, ECSArXivCrossRefClient
from website.preprints.tasks import format_preprint, update_preprint_share, on_preprint_updated, update_or_create_preprint_identifiers, update_or_enqueue_on_preprint_updated
from website.project.views.contributor import find_preprint_provider
from website.identifiers.clients import crossref
from website.util.share import format_user


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


class TestPreprintSpam(OsfTestCase):

    def setUp(self):
        super(TestPreprintSpam, self).setUp()

        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.node = ProjectFactory(creator=self.user, is_public=True)
        self.preprint_one = PreprintFactory(creator=self.user, project=self.node)
        self.preprint_two = PreprintFactory(creator=self.user, project=self.node, filename='preprint_file_two.txt')

    @mock.patch.object(settings, 'SPAM_CHECK_ENABLED', True)
    def test_preprints_get_marked_as_spammy_if_node_is_spammy(self):
        with mock.patch('osf.models.node.Node._get_spam_content', mock.Mock(return_value='some content!')):
            with mock.patch('osf.models.node.Node.do_check_spam', mock.Mock(return_value=True)):
                self.node.check_spam(self.user, None, None)
        self.preprint_one.reload()
        self.preprint_two.reload()
        assert_true(self.preprint_one.is_spammy)
        assert_true(self.preprint_two.is_spammy)

class TestSetPreprintFile(OsfTestCase):

    def setUp(self):
        super(TestSetPreprintFile, self).setUp()

        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.read_write_user = AuthUserFactory()
        self.read_write_user_auth = Auth(user=self.read_write_user)

        self.project = ProjectFactory(creator=self.user)
        self.file = OsfStorageFile.create(
            node=self.project,
            path='/panda.txt',
            name='panda.txt',
            materialized_path='/panda.txt')
        self.file.save()

        self.file_two = OsfStorageFile.create(
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
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=self.auth)
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
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=self.auth)
        self.project.reload()
        assert_false(self.project.is_public)
        self.preprint.set_published(True, auth=self.auth, save=True)
        self.project.reload()
        assert_true(self.project.is_public)

    def test_add_primary_file(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file, self.file)
        assert_equal(type(self.project.preprint_file), type(self.file))

    @assert_logs(NodeLog.PREPRINT_FILE_UPDATED, 'project')
    def test_change_primary_file(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file, self.file)

        self.preprint.set_primary_file(self.file_two, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file_two._id)

    def test_add_invalid_file(self):
        with assert_raises(AttributeError):
            self.preprint.set_primary_file('inatlanta', auth=self.auth, save=True)

    def test_deleted_file_creates_orphan(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        self.file.is_deleted = True
        self.file.save()
        assert_true(self.project.is_preprint_orphan)

    def test_preprint_created_date(self):
        self.preprint.set_primary_file(self.file, auth=self.auth, save=True)
        assert_equal(self.project.preprint_file._id, self.file._id)

        assert(self.preprint.created)
        assert_not_equal(self.project.created, self.preprint.created)

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
        initial_subjects = list(self.preprint.subjects.all())
        with assert_raises(PermissionsError):
            self.preprint.set_subjects([[SubjectFactory()._id]], auth=Auth(self.write_contrib))

        self.preprint.reload()
        assert_equal(initial_subjects, list(self.preprint.subjects.all()))

    def test_nonadmin_cannot_set_file(self):
        initial_file = self.preprint.primary_file
        file = OsfStorageFile.create(
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
        initial_subjects = list(self.preprint.subjects.all())
        self.preprint.set_subjects([[SubjectFactory()._id]], auth=Auth(self.user))

        self.preprint.reload()
        assert_not_equal(initial_subjects, list(self.preprint.subjects.all()))

    def test_admin_can_set_file(self):
        initial_file = self.preprint.primary_file
        file = OsfStorageFile.create(
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


class TestPreprintProvider(OsfTestCase):
    def setUp(self):
        super(TestPreprintProvider, self).setUp()
        self.preprint = PreprintFactory(provider=None, is_published=False)
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

    def test_find_provider(self):
        self.preprint.provider = self.provider
        self.preprint.save()
        self.preprint.reload()

        assert ('branded', self.provider) == find_preprint_provider(self.preprint.node)

    def test_top_level_subjects(self):
        subj_a = SubjectFactory(provider=self.provider, text='A')
        subj_b = SubjectFactory(provider=self.provider, text='B')
        subj_aa = SubjectFactory(provider=self.provider, text='AA', parent=subj_a)
        subj_ab = SubjectFactory(provider=self.provider, text='AB', parent=subj_a)
        subj_ba = SubjectFactory(provider=self.provider, text='BA', parent=subj_b)
        subj_bb = SubjectFactory(provider=self.provider, text='BB', parent=subj_b)
        subj_aaa = SubjectFactory(provider=self.provider, text='AAA', parent=subj_aa)

        some_other_provider = PreprintProviderFactory(name='asdfArxiv')
        subj_asdf = SubjectFactory(provider=some_other_provider)

        assert set(self.provider.top_level_subjects) == set([subj_a, subj_b])

    def test_all_subjects(self):
        subj_a = SubjectFactory(provider=self.provider, text='A')
        subj_b = SubjectFactory(provider=self.provider, text='B')
        subj_aa = SubjectFactory(provider=self.provider, text='AA', parent=subj_a)
        subj_ab = SubjectFactory(provider=self.provider, text='AB', parent=subj_a)
        subj_ba = SubjectFactory(provider=self.provider, text='BA', parent=subj_b)
        subj_bb = SubjectFactory(provider=self.provider, text='BB', parent=subj_b)
        subj_aaa = SubjectFactory(provider=self.provider, text='AAA', parent=subj_aa)

        some_other_provider = PreprintProviderFactory(name='asdfArxiv')
        subj_asdf = SubjectFactory(provider=some_other_provider)

        assert set(self.provider.all_subjects) == set([subj_a, subj_b, subj_aa, subj_ab, subj_ba, subj_bb, subj_aaa])

    def test_highlighted_subjects(self):
        subj_a = SubjectFactory(provider=self.provider, text='A')
        subj_b = SubjectFactory(provider=self.provider, text='B')
        subj_aa = SubjectFactory(provider=self.provider, text='AA', parent=subj_a)
        subj_ab = SubjectFactory(provider=self.provider, text='AB', parent=subj_a)
        subj_ba = SubjectFactory(provider=self.provider, text='BA', parent=subj_b)
        subj_bb = SubjectFactory(provider=self.provider, text='BB', parent=subj_b)
        subj_aaa = SubjectFactory(provider=self.provider, text='AAA', parent=subj_aa)

        assert self.provider.has_highlighted_subjects is False
        assert set(self.provider.highlighted_subjects) == set([subj_a, subj_b])
        subj_aaa.highlighted = True
        subj_aaa.save()
        assert self.provider.has_highlighted_subjects is True
        assert set(self.provider.highlighted_subjects) == set([subj_aaa])

class TestPreprintIdentifiers(OsfTestCase):
    def setUp(self):
        super(TestPreprintIdentifiers, self).setUp()
        self.user = AuthUserFactory()
        self.auth = Auth(user=self.user)
        self.preprint = PreprintFactory(is_published=False, creator=self.user)

    @mock.patch('website.preprints.tasks.update_doi_metadata_on_change')
    def test_update_or_create_preprint_identifiers_called(self, mock_update_doi):
        published_preprint = PreprintFactory(is_published=True, creator=self.user)
        update_or_create_preprint_identifiers(published_preprint)
        assert mock_update_doi.called
        assert mock_update_doi.call_count == 1

    @mock.patch('website.settings.CROSSREF_URL', 'http://test.osf.crossref.test')
    def test_correct_doi_client_called(self):
        osf_preprint = PreprintFactory(is_published=True, creator=self.user, provider=PreprintProviderFactory())
        assert isinstance(osf_preprint.get_doi_client(), CrossRefClient)
        ecsarxiv_preprint = PreprintFactory(is_published=True, creator=self.user, provider=PreprintProviderFactory(_id='ecsarxiv'))
        assert isinstance(ecsarxiv_preprint.get_doi_client(), ECSArXivCrossRefClient)

class TestOnPreprintUpdatedTask(OsfTestCase):
    def setUp(self):
        super(TestOnPreprintUpdatedTask, self).setUp()
        self.user = AuthUserFactory()
        if len(self.user.fullname.split(' ')) > 2:
            # Prevent unexpected keys ('suffix', 'additional_name')
            self.user.fullname = 'David Davidson'
            self.user.middle_names = ''
            self.user.suffix = ''
            self.user.save()

        self.auth = Auth(user=self.user)
        self.preprint = PreprintFactory()
        thesis_provider = PreprintProviderFactory(share_publish_type='Thesis')
        self.thesis = PreprintFactory(provider=thesis_provider)

        for pp in [self.preprint, self.thesis]:

            pp.node.add_tag('preprint', self.auth, save=False)
            pp.node.add_tag('spoderman', self.auth, save=False)
            pp.node.add_unregistered_contributor('BoJack Horseman', 'horse@man.org', Auth(pp.node.creator))
            pp.node.add_contributor(self.user, visible=False)
            pp.node.save()

            pp.node.creator.given_name = u'ZZYZ'
            if len(pp.node.creator.fullname.split(' ')) > 2:
                # Prevent unexpected keys ('suffix', 'additional_name')
                pp.node.creator.fullname = 'David Davidson'
                pp.node.creator.middle_names = ''
                pp.node.creator.suffix = ''
            pp.node.creator.save()

            pp.set_subjects([[SubjectFactory()._id]], auth=Auth(pp.node.creator))


    def tearDown(self):
        handlers.celery_before_request()
        super(TestOnPreprintUpdatedTask, self).tearDown()

    def test_update_or_enqueue_on_preprint_updated(self):
        first_subjects = [15]
        update_or_enqueue_on_preprint_updated(
            self.preprint._id,
            old_subjects=first_subjects,
            saved_fields={'contributors': True}
        )
        second_subjects = [16, 17]
        update_or_enqueue_on_preprint_updated(
            self.preprint._id,
            old_subjects=second_subjects,
            saved_fields={'title': 'Hello'}
        )
        updated_task = get_task_from_postcommit_queue(
            'website.preprints.tasks.on_preprint_updated',
            predicate=lambda task: task.kwargs['preprint_id'] == self.preprint._id
        )
        assert 'title' in updated_task.kwargs['saved_fields']
        assert 'contributors' in  updated_task.kwargs['saved_fields']
        assert set(first_subjects + second_subjects).issubset(updated_task.kwargs['old_subjects'])

    def test_format_preprint(self):
        res = format_preprint(self.preprint, self.preprint.provider.share_publish_type)

        assert set(gn['@type'] for gn in res) == {'creator', 'contributor', 'throughsubjects', 'subject', 'throughtags', 'tag', 'workidentifier', 'agentidentifier', 'person', 'preprint', 'workrelation', 'creativework'}

        nodes = dict(enumerate(res))
        preprint = nodes.pop(next(k for k, v in nodes.items() if v['@type'] == 'preprint'))
        assert preprint['title'] == self.preprint.node.title
        assert preprint['description'] == self.preprint.node.description
        assert preprint['is_deleted'] == (not self.preprint.is_published or not self.preprint.node.is_public or self.preprint.node.is_preprint_orphan)
        assert preprint['date_updated'] == self.preprint.modified.isoformat()
        assert preprint['date_published'] == self.preprint.date_published.isoformat()

        tags = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'tag']
        through_tags = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'throughtags']
        assert sorted(tag['@id'] for tag in tags) == sorted(tt['tag']['@id'] for tt in through_tags)
        assert sorted(tag['name'] for tag in tags) == ['preprint', 'spoderman']

        subjects = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'subject']
        through_subjects = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'throughsubjects']
        s_ids = [s['@id'] for s in subjects]
        ts_ids = [ts['subject']['@id'] for ts in through_subjects]
        cs_ids = [i for i in set(s.get('central_synonym', {}).get('@id') for s in subjects) if i]
        for ts in ts_ids:
            assert ts in s_ids
            assert ts not in cs_ids  # Only aliased subjects are connected to self.preprint
        for s in subjects:
            subject = Subject.objects.get(text=s['name'])
            assert s['uri'].endswith('v2/taxonomies/{}/'.format(subject._id))  # This cannot change
        assert set(subject['name'] for subject in subjects) == set([s.text for s in self.preprint.subjects.all()] + [s.bepress_subject.text for s in self.preprint.subjects.filter(bepress_subject__isnull=False)])

        people = sorted([nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'person'], key=lambda x: x['given_name'])
        expected_people = sorted([{
            '@type': 'person',
            'given_name': u'BoJack',
            'family_name': u'Horseman',
        }, {
            '@type': 'person',
            'given_name': self.user.given_name,
            'family_name': self.user.family_name,
        }, {
            '@type': 'person',
            'given_name': self.preprint.node.creator.given_name,
            'family_name': self.preprint.node.creator.family_name,
        }], key=lambda x: x['given_name'])
        for i, p in enumerate(expected_people):
            expected_people[i]['@id'] = people[i]['@id']

        assert people == expected_people

        creators = sorted([nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'creator'], key=lambda x: x['order_cited'])
        assert creators == [{
            '@id': creators[0]['@id'],
            '@type': 'creator',
            'order_cited': 0,
            'cited_as': u'{}'.format(self.preprint.node.creator.fullname),
            'agent': {'@id': [p['@id'] for p in people if p['given_name'] == self.preprint.node.creator.given_name][0], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }, {
            '@id': creators[1]['@id'],
            '@type': 'creator',
            'order_cited': 1,
            'cited_as': u'BoJack Horseman',
            'agent': {'@id': [p['@id'] for p in people if p['given_name'] == u'BoJack'][0], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }]

        contributors = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'contributor']
        assert contributors == [{
            '@id': contributors[0]['@id'],
            '@type': 'contributor',
            'cited_as': u'{}'.format(self.user.fullname),
            'agent': {'@id': [p['@id'] for p in people if p['given_name'] == self.user.given_name][0], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }]

        agentidentifiers = {nodes.pop(k)['uri'] for k, v in nodes.items() if v['@type'] == 'agentidentifier'}
        assert agentidentifiers == set([
            'mailto:' + self.user.username,
            'mailto:' + self.preprint.node.creator.username,
            self.user.profile_image_url(),
            self.preprint.node.creator.profile_image_url(),
        ]) | set(user.absolute_url for user in self.preprint.node.contributors)

        related_work = next(nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'creativework')
        assert set(related_work.keys()) == {'@id', '@type'}  # Empty except @id and @type

        osf_doi = next(nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'workidentifier' and 'doi' in v['uri'] and 'osf.io' in v['uri'])
        assert osf_doi['creative_work'] == {'@id': preprint['@id'], '@type': preprint['@type']}

        related_doi = next(nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'workidentifier' and 'doi' in v['uri'])
        assert related_doi['creative_work'] == related_work

        workidentifiers = [nodes.pop(k)['uri'] for k, v in nodes.items() if v['@type'] == 'workidentifier']
        assert workidentifiers == [urlparse.urljoin(settings.DOMAIN, self.preprint._id + '/')]

        relation = nodes.pop(nodes.keys()[0])
        assert relation == {'@id': relation['@id'], '@type': 'workrelation', 'related': {'@id': related_work['@id'], '@type': related_work['@type']}, 'subject': {'@id': preprint['@id'], '@type': preprint['@type']}}

        assert nodes == {}

    def test_format_thesis(self):
        res = format_preprint(self.thesis, self.thesis.provider.share_publish_type)

        assert set(gn['@type'] for gn in res) == {'creator', 'contributor', 'throughsubjects', 'subject', 'throughtags', 'tag', 'workidentifier', 'agentidentifier', 'person', 'thesis', 'workrelation', 'creativework'}

        nodes = dict(enumerate(res))
        thesis = nodes.pop(next(k for k, v in nodes.items() if v['@type'] == 'thesis'))
        assert thesis['title'] == self.thesis.node.title
        assert thesis['description'] == self.thesis.node.description

    def test_format_preprint_date_modified_node_updated(self):
        self.preprint.node.save()
        res = format_preprint(self.preprint, self.preprint.provider.share_publish_type)
        nodes = dict(enumerate(res))
        preprint = nodes.pop(next(k for k, v in nodes.items() if v['@type'] == 'preprint'))
        assert preprint['date_updated'] == self.preprint.node.modified.isoformat()

    def test_format_preprint_nones(self):
        self.preprint.node.tags = []
        self.preprint.date_published = None
        self.preprint.node.preprint_article_doi = None
        self.preprint.set_subjects([], auth=Auth(self.preprint.node.creator))

        res = format_preprint(self.preprint, self.preprint.provider.share_publish_type)

        assert self.preprint.provider != 'osf'
        assert set(gn['@type'] for gn in res) == {'creator', 'contributor', 'workidentifier', 'agentidentifier', 'person', 'preprint'}

        nodes = dict(enumerate(res))
        preprint = nodes.pop(next(k for k, v in nodes.items() if v['@type'] == 'preprint'))
        assert preprint['title'] == self.preprint.node.title
        assert preprint['description'] == self.preprint.node.description
        assert preprint['is_deleted'] == (not self.preprint.is_published or not self.preprint.node.is_public or self.preprint.node.is_preprint_orphan)
        assert preprint['date_updated'] == self.preprint.modified.isoformat()
        assert preprint.get('date_published') is None

        people = sorted([nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'person'], key=lambda x: x['given_name'])
        expected_people = sorted([{
            '@type': 'person',
            'given_name': u'BoJack',
            'family_name': u'Horseman',
        }, {
            '@type': 'person',
            'given_name': self.user.given_name,
            'family_name': self.user.family_name,
        }, {
            '@type': 'person',
            'given_name': self.preprint.node.creator.given_name,
            'family_name': self.preprint.node.creator.family_name,
        }], key=lambda x: x['given_name'])
        for i, p in enumerate(expected_people):
            expected_people[i]['@id'] = people[i]['@id']

        assert people == expected_people

        creators = sorted([nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'creator'], key=lambda x: x['order_cited'])
        assert creators == [{
            '@id': creators[0]['@id'],
            '@type': 'creator',
            'order_cited': 0,
            'cited_as': self.preprint.node.creator.fullname,
            'agent': {'@id': [p['@id'] for p in people if p['given_name'] == self.preprint.node.creator.given_name][0], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }, {
            '@id': creators[1]['@id'],
            '@type': 'creator',
            'order_cited': 1,
            'cited_as': u'BoJack Horseman',
            'agent': {'@id': [p['@id'] for p in people if p['given_name'] == u'BoJack'][0], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }]

        contributors = [nodes.pop(k) for k, v in nodes.items() if v['@type'] == 'contributor']
        assert contributors == [{
            '@id': contributors[0]['@id'],
            '@type': 'contributor',
            'cited_as': self.user.fullname,
            'agent': {'@id': [p['@id'] for p in people if p['given_name'] == self.user.given_name][0], '@type': 'person'},
            'creative_work': {'@id': preprint['@id'], '@type': preprint['@type']},
        }]

        agentidentifiers = {nodes.pop(k)['uri'] for k, v in nodes.items() if v['@type'] == 'agentidentifier'}
        assert agentidentifiers == set([
            'mailto:' + self.user.username,
            'mailto:' + self.preprint.node.creator.username,
            self.user.profile_image_url(),
            self.preprint.node.creator.profile_image_url(),
        ]) | set(user.absolute_url for user in self.preprint.node.contributors)

        workidentifiers = {nodes.pop(k)['uri'] for k, v in nodes.items() if v['@type'] == 'workidentifier'}
        # URLs should *always* be osf.io/guid/
        assert workidentifiers == set([urlparse.urljoin(settings.DOMAIN, self.preprint._id) + '/', 'http://dx.doi.org/{}'.format(self.preprint.get_identifier('doi').value)])

        assert nodes == {}

    def test_format_preprint_is_deleted(self):
        CASES = {
            'is_published': (True, False),
            'is_published': (False, True),
            'node.is_public': (True, False),
            'node.is_public': (False, True),
            'node._is_preprint_orphan': (True, True),
            'node._is_preprint_orphan': (False, False),
            'node.is_deleted': (True, True),
            'node.is_deleted': (False, False),
        }
        for key, (value, is_deleted) in CASES.items():
            target = self.preprint
            for k in key.split('.')[:-1]:
                if k:
                    target = getattr(target, k)
            orig_val = getattr(target, key.split('.')[-1])
            setattr(target, key.split('.')[-1], value)

            res = format_preprint(self.preprint, self.preprint.provider.share_publish_type)

            preprint = next(v for v in res if v['@type'] == 'preprint')
            assert preprint['is_deleted'] is is_deleted

            setattr(target, key.split('.')[-1], orig_val)

    def test_format_preprint_is_deleted_true_if_qatest_tag_is_added(self):
        res = format_preprint(self.preprint, self.preprint.provider.share_publish_type)
        preprint = next(v for v in res if v['@type'] == 'preprint')
        assert preprint['is_deleted'] is False

        self.preprint.node.add_tag('qatest', auth=self.auth, save=True)

        res = format_preprint(self.preprint, self.preprint.provider.share_publish_type)
        preprint = next(v for v in res if v['@type'] == 'preprint')
        assert preprint['is_deleted'] is True

    def test_unregistered_users_guids(self):
        user = UserFactory.build(is_registered=False)
        user.save()

        node = format_user(user)
        assert {x.attrs['uri'] for x in node.get_related()} == {user.absolute_url}

    def test_verified_orcid(self):
        user = UserFactory.build(is_registered=True)
        user.external_identity = {'ORCID': {'fake-orcid': 'VERIFIED'}}
        user.save()

        node = format_user(user)
        assert {x.attrs['uri'] for x in node.get_related()} == {'fake-orcid', user.absolute_url, user.profile_image_url()}

    def test_unverified_orcid(self):
        user = UserFactory.build(is_registered=True)
        user.external_identity = {'ORCID': {'fake-orcid': 'SOMETHINGELSE'}}
        user.save()

        node = format_user(user)
        assert {x.attrs['uri'] for x in node.get_related()} == {user.absolute_url, user.profile_image_url()}


class TestPreprintSaveShareHook(OsfTestCase):
    def setUp(self):
        super(TestPreprintSaveShareHook, self).setUp()
        self.admin = AuthUserFactory()
        self.auth = Auth(user=self.admin)
        self.provider = PreprintProviderFactory(name='Lars Larson Snowmobiling Experience')
        self.project = ProjectFactory(creator=self.admin, is_public=True)
        self.subject = SubjectFactory()
        self.subject_two = SubjectFactory()
        self.file = api_test_utils.create_test_file(self.project, self.admin, 'second_place.pdf')
        self.preprint = PreprintFactory(creator=self.admin, filename='second_place.pdf', provider=self.provider, subjects=[[self.subject._id]], project=self.project, is_published=False)

    @mock.patch('website.preprints.tasks.on_preprint_updated.si')
    def test_save_unpublished_not_called(self, mock_on_preprint_updated):
        self.preprint.save()
        assert not mock_on_preprint_updated.called

    @mock.patch('website.preprints.tasks.on_preprint_updated.si')
    def test_save_published_called(self, mock_on_preprint_updated):
        self.preprint.set_published(True, auth=self.auth, save=True)
        assert mock_on_preprint_updated.called

    # This covers an edge case where a preprint is forced back to unpublished
    # that it sends the information back to share
    @mock.patch('website.preprints.tasks.on_preprint_updated.si')
    def test_save_unpublished_called_forced(self, mock_on_preprint_updated):
        self.preprint.set_published(True, auth=self.auth, save=True)
        self.preprint.published = False
        self.preprint.save(**{'force_update': True})
        assert_equal(mock_on_preprint_updated.call_count, 2)

    @mock.patch('website.preprints.tasks.on_preprint_updated.si')
    def test_save_published_called(self, mock_on_preprint_updated):
        self.preprint.set_published(True, auth=self.auth, save=True)
        assert mock_on_preprint_updated.called

    @mock.patch('website.preprints.tasks.on_preprint_updated.si')
    def test_save_published_subject_change_called(self, mock_on_preprint_updated):
        self.preprint.is_published = True
        self.preprint.set_subjects([[self.subject_two._id]], auth=self.auth)
        assert mock_on_preprint_updated.called
        call_args, call_kwargs = mock_on_preprint_updated.call_args
        assert call_kwargs.get('old_subjects') == [self.subject.id]

    @mock.patch('website.preprints.tasks.on_preprint_updated.si')
    def test_save_unpublished_subject_change_not_called(self, mock_on_preprint_updated):
        self.preprint.set_subjects([[self.subject_two._id]], auth=self.auth)
        assert not mock_on_preprint_updated.called

    @mock.patch('website.preprints.tasks.requests')
    @mock.patch('website.preprints.tasks.settings.SHARE_URL', 'ima_real_website')
    def test_send_to_share_is_true(self, mock_requests):
        self.preprint.provider.access_token = 'Snowmobiling'
        self.preprint.provider.save()
        on_preprint_updated(self.preprint._id)

        assert mock_requests.post.called

    @mock.patch('osf.models.preprint_service.update_or_enqueue_on_preprint_updated')
    def test_node_contributor_changes_updates_preprints_share(self, mock_on_preprint_updated):
        # A user is added as a contributor
        self.preprint.is_published = True
        self.preprint.save()

        assert mock_on_preprint_updated.call_count == 1

        user = AuthUserFactory()
        node = self.preprint.node
        node.preprint_file = self.file

        node.add_contributor(contributor=user, auth=self.auth)
        assert mock_on_preprint_updated.call_count == 2

        node.move_contributor(contributor=user, index=0, auth=self.auth)
        assert mock_on_preprint_updated.call_count == 3

        data = [{'id': self.admin._id, 'permission': 'admin', 'visible': True},
                {'id': user._id, 'permission': 'write', 'visible': False}]
        node.manage_contributors(data, auth=self.auth, save=True)
        assert mock_on_preprint_updated.call_count == 4

        node.update_contributor(user, 'read', True, auth=self.auth, save=True)
        assert mock_on_preprint_updated.call_count == 5

        node.remove_contributor(contributor=user, auth=self.auth)
        assert mock_on_preprint_updated.call_count == 6

    @mock.patch('website.preprints.tasks.settings.SHARE_URL', 'a_real_url')
    @mock.patch('website.preprints.tasks._async_update_preprint_share.delay')
    @mock.patch('website.preprints.tasks.requests')
    def test_call_async_update_on_500_failure(self, requests, mock_async):
        self.preprint.provider.access_token = 'Snowmobiling'
        requests.post.return_value = MockShareResponse(501)
        update_preprint_share(self.preprint)
        assert mock_async.called

    @mock.patch('website.preprints.tasks.settings.SHARE_URL', 'a_real_url')
    @mock.patch('website.preprints.tasks.send_desk_share_preprint_error')
    @mock.patch('website.preprints.tasks._async_update_preprint_share.delay')
    @mock.patch('website.preprints.tasks.requests')
    def test_no_call_async_update_on_400_failure(self, requests, mock_async, mock_mail):
        self.preprint.provider.access_token = 'Snowmobiling'
        requests.post.return_value = MockShareResponse(400)
        update_preprint_share(self.preprint)
        assert not mock_async.called
        assert mock_mail.called


class TestPreprintConfirmationEmails(OsfTestCase):
    def setUp(self):
        super(TestPreprintConfirmationEmails, self).setUp()
        self.user = AuthUserFactory()
        self.write_contrib = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_contributor(self.write_contrib, permissions=[permissions.WRITE])
        self.preprint = PreprintFactory(project=self.project, provider=PreprintProviderFactory(_id='osf'), is_published=False)
        self.preprint_branded = PreprintFactory(creator=self.user, is_published=False)

    @mock.patch('website.mails.send_mail')
    def test_creator_gets_email(self, send_mail):
        self.preprint.set_published(True, auth=Auth(self.user), save=True)
        domain = self.preprint.provider.domain or settings.DOMAIN
        send_mail.assert_called_with(
            self.user.email,
            mails.REVIEWS_SUBMISSION_CONFIRMATION,
            user=self.user,
            mimetype='html',
            provider_url='{}preprints/{}'.format(domain, self.preprint.provider._id),
            domain=domain,
            provider_contact_email=settings.OSF_CONTACT_EMAIL,
            provider_support_email=settings.OSF_SUPPORT_EMAIL,
            workflow=None,
            reviewable=self.preprint,
            is_creator=True,
            provider_name=self.preprint.provider.name,
            no_future_emails=[],
            logo=settings.OSF_PREPRINTS_LOGO,
        )
        assert_equals(send_mail.call_count, 1)

        self.preprint_branded.set_published(True, auth=Auth(self.user), save=True)
        assert_equals(send_mail.call_count, 2)

@pytest.mark.django_db
class TestWithdrawnPreprint:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def unpublished_preprint_pre_mod(self):
        return PreprintFactory(provider__reviews_workflow='pre-moderation', is_published=False)

    @pytest.fixture()
    def preprint_pre_mod(self):
        return PreprintFactory(provider__reviews_workflow='pre-moderation')

    @pytest.fixture()
    def unpublished_preprint_post_mod(self):
        return PreprintFactory(provider__reviews_workflow='post-moderation', is_published=False)

    @pytest.fixture()
    def preprint_post_mod(self):
        return PreprintFactory(provider__reviews_workflow='post-moderation')

    @pytest.fixture()
    def preprint(self):
        return PreprintFactory()

    @pytest.fixture()
    def admin(self):
        admin = AuthUserFactory()
        osf_admin = Group.objects.get(name='osf_admin')
        admin.groups.add(osf_admin)
        return admin

    @pytest.fixture()
    def moderator(self, preprint_pre_mod, preprint_post_mod):
        moderator = AuthUserFactory()
        preprint_pre_mod.provider.add_to_group(moderator, 'moderator')
        preprint_pre_mod.provider.save()

        preprint_post_mod.provider.add_to_group(moderator, 'moderator')
        preprint_post_mod.provider.save()

        return moderator

    @pytest.fixture()
    def make_withdrawal_request(self, user):
        def withdrawal_request(target):
            request = PreprintRequestFactory(
                        creator=user,
                        target=target,
                        request_type=RequestTypes.WITHDRAWAL.value,
                        machine_state=DefaultStates.INITIAL.value)
            request.run_submit(user)
            return request
        return withdrawal_request

    @pytest.fixture()
    def crossref_client(self):
        return crossref.CrossRefClient(base_url='http://test.osf.crossref.test')


    def test_withdrawn_preprint(self, user, preprint, unpublished_preprint_pre_mod, unpublished_preprint_post_mod):
        # test_ever_public

        # non-moderated
        assert preprint.ever_public

        # pre-mod
        unpublished_preprint_pre_mod.run_submit(user)

        assert not unpublished_preprint_pre_mod.ever_public
        unpublished_preprint_pre_mod.run_reject(user, 'it')
        unpublished_preprint_pre_mod.reload()
        assert not unpublished_preprint_pre_mod.ever_public
        unpublished_preprint_pre_mod.run_accept(user, 'it')
        unpublished_preprint_pre_mod.reload()
        assert unpublished_preprint_pre_mod.ever_public

        # post-mod
        unpublished_preprint_post_mod.run_submit(user)
        assert unpublished_preprint_post_mod.ever_public

        # test_cannot_set_ever_public_to_False
        unpublished_preprint_pre_mod.ever_public = False
        unpublished_preprint_post_mod.ever_public = False
        preprint.ever_public = False
        with pytest.raises(ValidationError):
            preprint.save()
        with pytest.raises(ValidationError):
            unpublished_preprint_pre_mod.save()
        with pytest.raises(ValidationError):
            unpublished_preprint_post_mod.save()

    def test_crossref_status_is_updated(self, make_withdrawal_request, preprint, preprint_post_mod, preprint_pre_mod, moderator, admin, crossref_client):
        # test_non_moderated_preprint
        assert preprint.verified_publishable
        assert crossref_client.get_status(preprint) == 'public'

        withdrawal_request = make_withdrawal_request(preprint)
        withdrawal_request.run_accept(admin, withdrawal_request.comment)

        assert preprint.is_retracted
        assert not preprint.verified_publishable
        assert crossref_client.get_status(preprint) == 'unavailable'

        # test_post_moderated_preprint
        assert preprint_post_mod.verified_publishable
        assert crossref_client.get_status(preprint_post_mod) == 'public'

        withdrawal_request = make_withdrawal_request(preprint_post_mod)
        withdrawal_request.run_accept(moderator, withdrawal_request.comment)

        assert preprint_post_mod.is_retracted
        assert not preprint_post_mod.verified_publishable
        assert crossref_client.get_status(preprint_post_mod) == 'unavailable'

        # test_pre_moderated_preprint
        assert preprint_pre_mod.verified_publishable
        assert crossref_client.get_status(preprint_pre_mod) == 'public'

        withdrawal_request = make_withdrawal_request(preprint_pre_mod)
        withdrawal_request.run_accept(moderator, withdrawal_request.comment)

        assert preprint_pre_mod.is_retracted
        assert not preprint_pre_mod.verified_publishable
        assert crossref_client.get_status(preprint_pre_mod) == 'unavailable'
