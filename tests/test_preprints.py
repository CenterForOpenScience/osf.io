# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa (PEP8 asserts)
import mock
import urlparse

from addons.osfstorage.models import OsfStorageFile
from api_tests import utils as api_test_utils
from framework.auth import Auth
from framework.celery_tasks import handlers
from framework.exceptions import PermissionsError
from osf.models import NodeLog, Subject
from osf_tests.factories import (
    AuthUserFactory,
    PreprintFactory,
    PreprintProviderFactory,
    ProjectFactory,
    SubjectFactory,
    UserFactory,
)
from osf_tests.utils import MockShareResponse
from osf.utils import permissions
from tests.utils import assert_logs
from tests.base import OsfTestCase
from website import settings, mails
from website.identifiers.utils import get_doi_and_metadata_for_object
from website.preprints.tasks import format_preprint, update_preprint_share, on_preprint_updated
from website.project.views.contributor import find_preprint_provider
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

    @mock.patch('website.preprints.tasks.get_and_set_preprint_identifiers.si')
    def test_identifiers_task_called_on_publish(self, mock_get_and_set_identifiers):
        assert self.preprint.identifiers.count() == 0
        self.preprint.set_published(True, auth=self.auth, save=True)

        assert mock_get_and_set_identifiers.called

    def test_get_doi_for_preprint(self):
        new_provider = PreprintProviderFactory()
        preprint = PreprintFactory(provider=new_provider)
        ideal_doi = '{}osf.io/{}'.format(settings.DOI_NAMESPACE, preprint._id)

        doi, metadata = get_doi_and_metadata_for_object(preprint)

        assert doi == ideal_doi

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
        assert {'old_subjects': [self.subject.id]} in mock_on_preprint_updated.call_args

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

    @mock.patch('website.preprints.tasks.on_preprint_updated.si')
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

        send_mail.assert_called_with(
            self.user.email,
            mails.PREPRINT_CONFIRMATION_DEFAULT,
            user=self.user,
            node=self.preprint.node,
            preprint=self.preprint,
            osf_contact_email=settings.OSF_CONTACT_EMAIL
        )

        assert_equals(send_mail.call_count, 1)

        self.preprint_branded.set_published(True, auth=Auth(self.user), save=True)
        assert_equals(send_mail.call_count, 2)
