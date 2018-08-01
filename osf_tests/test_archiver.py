#-*- coding: utf-8 -*-
import copy
import datetime
import functools
import json
import logging
import random
import re
from contextlib import nested

import celery
import responses
import mock  # noqa
from django.utils import timezone
from django.db import IntegrityError
from mock import call
import pytest
from nose.tools import *  # flake8: noqa

from framework.auth import Auth
from framework.celery_tasks import handlers

from website.archiver import (
    ARCHIVER_INITIATED,
    ARCHIVER_SUCCESS,
    ARCHIVER_FAILURE,
    ARCHIVER_NETWORK_ERROR,
    ARCHIVER_SIZE_EXCEEDED,
    NO_ARCHIVE_LIMIT,
)
from website.archiver import utils as archiver_utils
from website.archiver.tasks import ArchivedFileNotFound
from website.app import *  # noqa
from website.archiver import listeners
from website.archiver.tasks import *   # noqa
from osf.models.archive import ArchiveTarget, ArchiveJob
from website.archiver.decorators import fail_archive_on_error

from website import mails
from website import settings
from osf.models import RegistrationSchema, Registration
from osf.utils.sanitize import strip_html
from addons.base.models import BaseStorageAddon
from api.base.utils import waterbutler_api_url_for

from osf_tests import factories
from tests.base import OsfTestCase, fake
from tests import utils as test_utils
from tests.utils import unique as _unique

pytestmark = pytest.mark.django_db

SILENT_LOGGERS = (
    'framework.celery_tasks.utils',
    'website.app',
    'website.archiver.tasks',
)
for each in SILENT_LOGGERS:
    logging.getLogger(each).setLevel(logging.CRITICAL)

sha256_factory = _unique(fake.sha256)
name_factory = _unique(fake.ean13)

def file_factory(name=None, sha256=None):
    fname = name or name_factory()
    return {
        'path': '/' + fname,
        'name': fname,
        'kind': 'file',
        'size': random.randint(4, 4000),
        'extra': {
            'hashes': {
                'sha256': sha256 or sha256_factory()
            }
        }
    }

def folder_factory(depth, num_files, num_folders, path_above):
    new_path = os.path.join(path_above.rstrip('/'), fake.word())
    return {
        'path': new_path,
        'kind': 'folder',
        'children': [
            file_factory()
            for i in range(num_files)
        ] + [
            folder_factory(depth - 1, num_files, num_folders, new_path)
        ] if depth > 0 else []
    }

def file_tree_factory(depth, num_files, num_folders):
    return {
        'path': '/',
        'kind': 'folder',
        'children': [
            file_factory()
            for i in range(num_files)
        ] + [
            folder_factory(depth - 1, num_files, num_folders, '/')
        ] if depth > 0 else []
    }

def select_files_from_tree(file_tree):
    """
    Select a file from every depth of a file_tree. This implementation relies on:
      - every folder has a subtree of equal depth (i.e. any folder selection is
      adequate to select a file from the maximum depth)
    The file_tree_factory fulfills this condition.
    """
    selected = {}
    stack = [file_tree]
    while len(stack):
        file_node = stack.pop(0)
        target_files = [f for f in file_node['children'] if f['kind'] == 'file']
        if target_files:
            target_file = target_files[0]
            selected[target_file['extra']['hashes']['sha256']] = target_file
        target_folders = [f for f in file_node['children'] if f['kind'] == 'folder']
        if target_folders:
            stack.append(target_folders[0])
    return selected

FILE_TREE = {
    'path': '/',
    'name': '',
    'kind': 'folder',
    'size': '100',
    'children': [
        {
            'path': '/1234567',
            'name': 'Afile.file',
            'kind': 'file',
            'size': '128',
        },
        {
            'path': '/qwerty',
            'name': 'A Folder',
            'kind': 'folder',
            'children': [
                {
                    'path': '/qwerty/asdfgh',
                    'name': 'coolphoto.png',
                    'kind': 'file',
                    'size': '256',
                }
            ],
        }
    ],
}

WB_FILE_TREE = {
    'attributes': {
        'path': '/',
        'name': '',
        'kind': 'folder',
        'size': '100',
        'children': [
            {
                'attributes': {
                    'path': '/1234567',
                    'name': 'Afile.file',
                    'kind': 'file',
                    'size': '128',
                }
            },
            {
                'attributes': {
                    'path': '/qwerty',
                    'name': 'A Folder',
                    'kind': 'folder',
                    'children': [
                        {
                            'attributes': {
                                'path': '/qwerty/asdfgh',
                                'name': 'coolphoto.png',
                                'kind': 'file',
                                'size': '256',
                            }
                        }
                    ],
                }
            }
       ],
    }
}


class MockAddon(object):

    complete = True
    config = mock.MagicMock()

    def __init__(self, **kwargs):
        self._id = fake.md5()

    def _get_file_tree(self, user, version):
        return FILE_TREE

    def after_register(self, *args):
        return None, None

    @property
    def archive_folder_name(self):
        return 'Some Archive'

    def archive_errors(self):
        return False

mock_osfstorage = MockAddon()
mock_osfstorage.config.short_name = 'osfstorage'
mock_dropbox = MockAddon()
mock_dropbox.config.short_name = 'dropbox'

active_addons = {'osfstorage', 'dropbox'}

def _mock_get_addon(name, *args, **kwargs):
    if name not in active_addons:
        return None
    if name == 'dropbox':
        return mock_dropbox
    if name == 'osfstorage':
        return mock_osfstorage

def _mock_delete_addon(name, *args, **kwargs):
    try:
        active_addons.remove(name)
    except ValueError:
        pass

def _mock_get_or_add(name, *args, **kwargs):
    active_addons.add(name)
    return _mock_get_addon(name)

def use_fake_addons(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with nested(
            mock.patch('osf.models.mixins.AddonModelMixin.add_addon', mock.Mock(side_effect=_mock_get_or_add)),
            mock.patch('osf.models.mixins.AddonModelMixin.get_addon', mock.Mock(side_effect=_mock_get_addon)),
            mock.patch('osf.models.mixins.AddonModelMixin.delete_addon', mock.Mock(side_effect=_mock_delete_addon)),
            mock.patch('osf.models.mixins.AddonModelMixin.get_or_add_addon', mock.Mock(side_effect=_mock_get_or_add))
        ):
            ret = func(*args, **kwargs)
            return ret
    return wrapper

def generate_file_tree(nodes):
    file_trees = {
        n._id: file_tree_factory(3, 3, 3)
        for n in nodes
    }

    selected_files = {}
    selected_file_node_index = {}
    for n in nodes:
        file_tree = file_trees[n._id]
        selected = select_files_from_tree(file_tree)
        selected_file_node_index.update({
            sha256: n._id
            for sha256 in selected.keys()
        })
        selected_files.update(selected)  # select files from each Node
    return file_trees, selected_files, selected_file_node_index

def generate_schema_from_data(data):
    def from_property(id, prop):
        if isinstance(prop.get('value'), dict):
            return {
                'id': id,
                'type': 'object',
                'properties': [
                    from_property(pid, sp)
                    for pid, sp in prop['value'].items()
                ]
            }
        else:
            return {
                'id': id,
                'type': 'osf-upload' if prop.get('extra') else 'string'
            }
    def from_question(qid, question):
        if q.get('extra'):
            return {
                'qid': qid,
                'type': 'osf-upload'
            }
        elif isinstance(q.get('value'), dict):
            return {
                'qid': qid,
                'type': 'object',
                'properties': [
                    from_property(id, value)
                    for id, value in question.get('value').items()
                ]
            }
        else:
            return {
                'qid': qid,
                'type': 'string'
            }
    _schema = {
        'name': 'Test',
        'version': 2,
        'config': {
            'hasFiles': True
        },
        'pages': [{
            'id': 'page1',
            'questions': [
                from_question(qid, q)
                for qid, q in data.items()
            ]
        }]
    }
    schema = RegistrationSchema(
        name=_schema['name'],
        schema_version=_schema['version'],
        schema=_schema
    )
    try:
        schema.save()
    except IntegrityError:

        # Unfortunately, we don't have db isolation between test cases for some
        # reason. Update the doc currently in the db rather than saving a new
        # one.

        schema = RegistrationSchema.objects.get(name=_schema['name'], schema_version=_schema['version'])
        schema.schema = _schema
        schema.save()

    return schema

def generate_metadata(file_trees, selected_files, node_index):
    data = {}
    uploader_types = {
        ('q_' + selected_file['name']): {
            'value': fake.word(),
            'extra': [{
                'sha256': sha256,
                'viewUrl': '/project/{0}/files/osfstorage{1}'.format(
                    node_index[sha256],
                    selected_file['path']
                ),
                'selectedFileName': selected_file['name'],
                'nodeId': node_index[sha256]
            }]
        }
        for sha256, selected_file in selected_files.items()
    }
    data.update(uploader_types)
    object_types = {
        ('q_' + selected_file['name'] + '_obj'): {
            'value': {
                name_factory(): {
                    'value': fake.word(),
                    'extra': [{
                        'sha256': sha256,
                        'viewUrl': '/project/{0}/files/osfstorage{1}'.format(
                            node_index[sha256],
                            selected_file['path']
                        ),
                        'selectedFileName': selected_file['name'],
                        'nodeId': node_index[sha256]
                    }]
                },
                name_factory(): {
                    'value': fake.word()
                }
            }
        }
        for sha256, selected_file in selected_files.items()
    }
    data.update(object_types)
    other_questions = {
        'q{}'.format(i): {
            'value': fake.word()
        }
        for i in range(5)
    }
    data.update(other_questions)
    return data

class ArchiverTestCase(OsfTestCase):

    def setUp(self):
        super(ArchiverTestCase, self).setUp()

        handlers.celery_before_request()
        self.user = factories.UserFactory()
        self.auth = Auth(user=self.user)
        self.src = factories.NodeFactory(creator=self.user)
        self.dst = factories.RegistrationFactory(user=self.user, project=self.src, send_signals=False, archive=True)
        archiver_utils.before_archive(self.dst, self.user)
        self.archive_job = self.dst.archive_job

class TestStorageAddonBase(ArchiverTestCase):
    tree_root = WB_FILE_TREE['attributes']['children']
    tree_child = tree_root[0]
    tree_grandchild = tree_root[1]['attributes']['children']
    tree_great_grandchild = tree_grandchild[0]

    URLS = ['/', '/1234567', '/qwerty', '/qwerty/asdfgh']

    def get_resp(self, url):
        if '/qwerty/asdfgh' in url:
            return dict(data=self.tree_great_grandchild)
        if '/qwerty' in url:
            return dict(data=self.tree_grandchild)
        if '/1234567' in url:
            return dict(data=self.tree_child)
        return dict(data=self.tree_root)

    @responses.activate
    def _test__get_file_tree(self, addon_short_name):
        for path in self.URLS:
            url = waterbutler_api_url_for(
                self.src.osfstorage_region.waterbutler_url,
                self.src._id,
                addon_short_name,
                meta=True,
                path=path,
                user=self.user,
                view_only=True,
                _internal=True,
            )
            responses.add(
                responses.Response(
                    responses.GET,
                    url,
                    json=self.get_resp(url),
                    content_type='applcation/json'
                )
            )
        addon = self.src.get_or_add_addon(addon_short_name, auth=self.auth)
        root = {
            'path': '/',
            'name': '',
            'kind': 'folder',
            # Regression test for OSF-8696 confirming that size attr does not stop folders from recursing
            'size': '100',
        }
        file_tree = addon._get_file_tree(root, self.user)
        assert_equal(FILE_TREE, file_tree)
        assert_equal(len(responses.calls), 2)

        # Makes a request for folders ('/qwerty') but not files ('/1234567', '/qwerty/asdfgh')
        requests_made_urls = [call.request.url for call in responses.calls]
        assert_true(any('/qwerty' in url for url in requests_made_urls))
        assert_false(any('/1234567' in url for url in requests_made_urls))
        assert_false(any('/qwerty/asdfgh' in url for url in requests_made_urls))

    def _test_addon(self, addon_short_name):
        self._test__get_file_tree(addon_short_name)

    # @pytest.mark.skip('Unskip when figshare addon is implemented')
    def test_addons(self):
        #  Test that each addon in settings.ADDONS_ARCHIVABLE other than wiki/forward implements the StorageAddonBase interface
        for addon in [a for a in settings.ADDONS_ARCHIVABLE if a not in ['wiki', 'forward']]:
            self._test_addon(addon)

class TestArchiverTasks(ArchiverTestCase):

    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    @mock.patch('celery.chain')
    def test_archive(self, mock_chain, mock_enqueue):
        archive(job_pk=self.archive_job._id)
        targets = [self.src.get_addon(name) for name in settings.ADDONS_ARCHIVABLE]
        target_addons = [addon for addon in targets if (addon and addon.complete and isinstance(addon, BaseStorageAddon))]
        assert_true(self.dst.archiving)
        mock_chain.assert_called_with(
            [
                celery.group(
                    stat_addon.si(
                        addon_short_name=addon.config.short_name,
                        job_pk=self.archive_job._id,
                    ) for addon in target_addons
                ),
                archive_node.s(job_pk=self.archive_job._id)
            ]
        )

    def test_stat_addon(self):
        with mock.patch.object(BaseStorageAddon, '_get_file_tree') as mock_file_tree:
            mock_file_tree.return_value = FILE_TREE
            res = stat_addon('osfstorage', self.archive_job._id)
        assert_equal(res.target_name, 'osfstorage')
        assert_equal(res.disk_usage, 128 + 256)

    @mock.patch('website.archiver.tasks.archive_addon.delay')
    def test_archive_node_pass(self, mock_archive_addon):
        settings.MAX_ARCHIVE_SIZE = 1024 ** 3
        with mock.patch.object(BaseStorageAddon, '_get_file_tree') as mock_file_tree:
            mock_file_tree.return_value = FILE_TREE
            results = [stat_addon(addon, self.archive_job._id) for addon in ['osfstorage']]
        with mock.patch.object(celery, 'group') as mock_group:
            archive_node(results, self.archive_job._id)
        archive_osfstorage_signature = archive_addon.si(
            'osfstorage',
            self.archive_job._id
        )
        assert(mock_group.called_with(archive_osfstorage_signature))

    @use_fake_addons
    def test_archive_node_fail(self):
        settings.MAX_ARCHIVE_SIZE = 100
        results = [stat_addon(addon, self.archive_job._id) for addon in ['osfstorage', 'dropbox']]
        with pytest.raises(ArchiverSizeExceeded):  # Note: Requires task_eager_propagates = True in celery
            archive_node.apply(args=(results, self.archive_job._id))

    @mock.patch('website.project.signals.archive_callback.send')
    @mock.patch('website.archiver.tasks.archive_addon.delay')
    def test_archive_node_does_not_archive_empty_addons(self, mock_archive_addon, mock_send):
        with mock.patch('osf.models.mixins.AddonModelMixin.get_addon') as mock_get_addon:
            mock_addon = MockAddon()
            def empty_file_tree(user, version):
                return {
                    'path': '/',
                    'kind': 'folder',
                    'name': 'Fake',
                    'children': []
                }
            setattr(mock_addon, '_get_file_tree', empty_file_tree)
            mock_get_addon.return_value = mock_addon
            results = [stat_addon(addon, self.archive_job._id) for addon in ['osfstorage']]
            archive_node(results, job_pk=self.archive_job._id)
        assert_false(mock_archive_addon.called)
        assert_true(mock_send.called)

    @use_fake_addons
    @mock.patch('website.archiver.tasks.archive_addon.delay')
    def test_archive_node_no_archive_size_limit(self, mock_archive_addon):
        settings.MAX_ARCHIVE_SIZE = 100
        self.archive_job.initiator.add_system_tag(NO_ARCHIVE_LIMIT)
        self.archive_job.initiator.save()
        with mock.patch.object(BaseStorageAddon, '_get_file_tree') as mock_file_tree:
            mock_file_tree.return_value = FILE_TREE
            results = [stat_addon(addon, self.archive_job._id) for addon in ['osfstorage', 'dropbox']]
        with mock.patch.object(celery, 'group') as mock_group:
            archive_node(results, self.archive_job._id)
        archive_dropbox_signature = archive_addon.si(
            'dropbox',
            self.archive_job._id
        )
        assert(mock_group.called_with(archive_dropbox_signature))

    @mock.patch('website.archiver.tasks.make_copy_request.delay')
    def test_archive_addon(self, mock_make_copy_request):
        archive_addon('osfstorage', self.archive_job._id)
        assert_equal(self.archive_job.get_target('osfstorage').status, ARCHIVER_INITIATED)
        cookie = self.user.get_or_create_cookie()
        assert(mock_make_copy_request.called_with(
            self.archive_job._id,
            settings.WATERBUTLER_URL + '/ops/copy',
            data=dict(
                source=dict(
                    cookie=cookie,
                    nid=self.src._id,
                    provider='osfstorage',
                    path='/',
                ),
                destination=dict(
                    cookie=cookie,
                    nid=self.dst._id,
                    provider=settings.ARCHIVE_PROVIDER,
                    path='/',
                ),
                rename='Archive of OSF Storage',
            )
        ))

    def test_archive_success(self):
        node = factories.NodeFactory(creator=self.user)
        file_trees, selected_files, node_index = generate_file_tree([node])
        data = generate_metadata(
            file_trees,
            selected_files,
            node_index
        )
        schema = generate_schema_from_data(data)
        with test_utils.mock_archive(node, schema=schema, data=data, autocomplete=True, autoapprove=True) as registration:
            with mock.patch.object(BaseStorageAddon, '_get_file_tree', mock.Mock(return_value=file_trees[node._id])):
                job = factories.ArchiveJobFactory(initiator=registration.creator)
                archive_success(registration._id, job._id)
                registration.reload()
                for key, question in registration.registered_meta[schema._id].items():
                    target = None
                    if isinstance(question.get('value'), dict):
                        target = [v for v in question['value'].values() if 'extra' in v and 'sha256' in v['extra'][0]][0]
                    elif 'extra' in question and 'hashes' in question['extra'][0]:
                        target = question
                    if target:
                        assert_in(registration._id, target['extra'][0]['viewUrl'])
                        assert_not_in(node._id, target['extra'][0]['viewUrl'])
                        del selected_files[target['extra'][0]['sha256']]
                    else:
                        # check non-file questions are unmodified
                        assert_equal(data[key]['value'], question['value'])
                assert_false(selected_files)

    def test_archive_success_escaped_file_names(self):
        file_tree = file_tree_factory(0, 0, 0)
        fake_file = file_factory(name='>and&and<')
        fake_file_name = strip_html(fake_file['name'])
        file_tree['children'] = [fake_file]

        node = factories.NodeFactory(creator=self.user)
        data = {
            ('q_' + fake_file_name): {
                'value': fake.word(),
                'extra': [{
                    'sha256': fake_file['extra']['hashes']['sha256'],
                    'viewUrl': '/project/{0}/files/osfstorage{1}'.format(
                        node._id,
                        fake_file['path']
                    ),
                    'selectedFileName': fake_file_name,
                    'nodeId': node._id
                }]
            }
        }
        schema = generate_schema_from_data(data)
        draft = factories.DraftRegistrationFactory(branched_from=node, registration_schema=schema, registered_metadata=data)

        with test_utils.mock_archive(node, schema=schema, data=data, autocomplete=True, autoapprove=True) as registration:
            with mock.patch.object(BaseStorageAddon, '_get_file_tree', mock.Mock(return_value=file_tree)):
                job = factories.ArchiveJobFactory(initiator=registration.creator)
                archive_success(registration._id, job._id)
                registration.reload()
                for key, question in registration.registered_meta[schema._id].items():
                    assert_equal(question['extra'][0]['selectedFileName'], fake_file_name)

    def test_archive_success_with_deeply_nested_schema(self):
        node = factories.NodeFactory(creator=self.user)
        file_trees, selected_files, node_index = generate_file_tree([node])
        data = {
            ('q_' + selected_file['name']): {
                'value': fake.word(),
                'extra': [{
                    'selectedFileName': selected_file['name'],
                    'nodeId': node._id,
                    'sha256': sha256,
                    'viewUrl': '/project/{0}/files/osfstorage{1}'.format(node._id, selected_file['path'])
                }]
            }
            for sha256, selected_file in selected_files.items()
        }
        schema = generate_schema_from_data(data)
        with test_utils.mock_archive(node, schema=schema, data=data, autocomplete=True, autoapprove=True) as registration:
            with mock.patch.object(BaseStorageAddon, '_get_file_tree', mock.Mock(return_value=file_trees[node._id])):
                job = factories.ArchiveJobFactory(initiator=registration.creator)
                archive_success(registration._id, job._id)
                registration.reload()
                for key, question in registration.registered_meta[schema._id].items():
                    target = None
                    if isinstance(question['value'], dict):
                        target = [v for v in question['value'].values() if 'extra' in v and 'sha256' in v['extra'][0]][0]
                    elif 'extra' in question and 'sha256' in question['extra'][0]:
                        target = question
                    if target:
                        assert_in(registration._id, target['extra'][0]['viewUrl'])
                        assert_not_in(node._id, target['extra'][0]['viewUrl'])
                        del selected_files[target['extra'][0]['sha256']]
                    else:
                        # check non-file questions are unmodified
                        assert_equal(data[key]['value'], question['value'])
                assert_false(selected_files)

    def test_archive_success_with_components(self):
        node = factories.NodeFactory(creator=self.user)
        comp1 = factories.NodeFactory(parent=node, creator=self.user)
        factories.NodeFactory(parent=comp1, creator=self.user)
        factories.NodeFactory(parent=node, creator=self.user)
        nodes = [n for n in node.node_and_primary_descendants()]
        file_trees, selected_files, node_index = generate_file_tree(nodes)
        data = generate_metadata(
            file_trees,
            selected_files,
            node_index
        )
        schema = generate_schema_from_data(data)

        with test_utils.mock_archive(node, schema=schema, data=copy.deepcopy(data), autocomplete=True, autoapprove=True) as registration:
            def mock_get_file_tree(self, *args, **kwargs):
                return file_trees[self.owner.registered_from._id]
            with mock.patch.object(BaseStorageAddon, '_get_file_tree', mock_get_file_tree):
                job = factories.ArchiveJobFactory(initiator=registration.creator)
                archive_success(registration._id, job._id)

            registration.reload()

            for key, question in registration.registered_meta[schema._id].items():
                target = None
                if isinstance(question['value'], dict):
                    target = [v for v in question['value'].values() if 'extra' in v and 'sha256' in v['extra'][0]]
                elif 'extra' in question and 'sha256' in question['extra']:
                    target = question

                if target:
                    node_id = re.search(
                        r'^/project/(?P<node_id>\w{5}).+$',
                        target[0]['extra'][0]['viewUrl']
                    ).groupdict()['node_id']
                    assert_in(
                        node_id,
                        [r._id for r in registration.node_and_primary_descendants()]
                    )
                    if target[0]['extra'][0]['sha256'] in selected_files:
                        del selected_files[target[0]['extra'][0]['sha256']]
                else:
                    # check non-file questions are unmodified
                    assert_equal(data[key]['value'], question['value'])
            # ensure each selected file was checked
            assert_false(selected_files)

    def test_archive_success_different_name_same_sha(self):
        file_tree = file_tree_factory(0, 0, 0)
        fake_file = file_factory()
        fake_file2 = file_factory(sha256=fake_file['extra']['hashes']['sha256'])
        file_tree['children'] = [fake_file, fake_file2]

        node = factories.NodeFactory(creator=self.user)
        data = {
            ('q_' + fake_file['name']): {
                'value': fake.word(),
                'extra': [{
                    'sha256': fake_file['extra']['hashes']['sha256'],
                    'viewUrl': '/project/{0}/files/osfstorage{1}'.format(
                        node._id,
                        fake_file['path']
                    ),
                    'selectedFileName': fake_file['name'],
                    'nodeId': node._id
                }]
            }
        }
        schema = generate_schema_from_data(data)

        with test_utils.mock_archive(node, schema=schema, data=data, autocomplete=True, autoapprove=True) as registration:
            with mock.patch.object(BaseStorageAddon, '_get_file_tree', mock.Mock(return_value=file_tree)):
                job = factories.ArchiveJobFactory(initiator=registration.creator)
                archive_success(registration._id, job._id)
                for key, question in registration.registered_meta[schema._id].items():
                    assert_equal(question['extra'][0]['selectedFileName'], fake_file['name'])

    def test_archive_failure_different_name_same_sha(self):
        file_tree = file_tree_factory(0, 0, 0)
        fake_file = file_factory()
        fake_file2 = file_factory(sha256=fake_file['extra']['hashes']['sha256'])
        file_tree['children'] = [fake_file2]

        node = factories.NodeFactory(creator=self.user)
        data = {
            ('q_' + fake_file['name']): {
                'value': fake.word(),
                'extra': [{
                    'sha256': fake_file['extra']['hashes']['sha256'],
                    'viewUrl': '/project/{0}/files/osfstorage{1}'.format(
                        node._id,
                        fake_file['path']
                    ),
                    'selectedFileName': fake_file['name'],
                    'nodeId': node._id
                }]
            }
        }
        schema = generate_schema_from_data(data)
        draft = factories.DraftRegistrationFactory(branched_from=node, registration_schema=schema, registered_metadata=data)

        with test_utils.mock_archive(node, schema=schema, data=data, autocomplete=True, autoapprove=True) as registration:
            with mock.patch.object(BaseStorageAddon, '_get_file_tree', mock.Mock(return_value=file_tree)):
                job = factories.ArchiveJobFactory(initiator=registration.creator)
                draft.registered_node = registration
                draft.save()
                with assert_raises(ArchivedFileNotFound):
                    archive_success(registration._id, job._id)

    def test_archive_success_same_file_in_component(self):
        file_tree = file_tree_factory(3, 3, 3)
        selected = select_files_from_tree(file_tree).values()[0]

        child_file_tree = file_tree_factory(0, 0, 0)
        child_file_tree['children'] = [selected]

        node = factories.NodeFactory(creator=self.user)
        child = factories.NodeFactory(creator=self.user, parent=node)

        data = {
            ('q_' + selected['name']): {
                'value': fake.word(),
                'extra': [{
                    'sha256': selected['extra']['hashes']['sha256'],
                    'viewUrl': '/project/{0}/files/osfstorage{1}'.format(
                        child._id,
                        selected['path']
                    ),
                    'selectedFileName': selected['name'],
                    'nodeId': child._id
                }]
            }
        }
        schema = generate_schema_from_data(data)

        with test_utils.mock_archive(node, schema=schema, data=data, autocomplete=True, autoapprove=True) as registration:
            with mock.patch.object(BaseStorageAddon, '_get_file_tree', mock.Mock(return_value=file_tree)):
                job = factories.ArchiveJobFactory(initiator=registration.creator)
                archive_success(registration._id, job._id)
                registration.reload()
                child_reg = registration.nodes[0]
                for key, question in registration.registered_meta[schema._id].items():
                    assert_in(child_reg._id, question['extra'][0]['viewUrl'])


class TestArchiverUtils(ArchiverTestCase):

    @mock.patch('website.mails.send_mail')
    def test_handle_archive_fail(self, mock_send_mail):
        archiver_utils.handle_archive_fail(
            ARCHIVER_NETWORK_ERROR,
            self.src,
            self.dst,
            self.user,
            {}
        )
        assert_equal(mock_send_mail.call_count, 2)
        assert_true(self.dst.is_deleted)

    @mock.patch('website.mails.send_mail')
    def test_handle_archive_fail_copy(self, mock_send_mail):
        url = settings.INTERNAL_DOMAIN + self.src._id
        archiver_utils.handle_archive_fail(
            ARCHIVER_NETWORK_ERROR,
            self.src,
            self.dst,
            self.user,
            {}
        )
        args_user = dict(
            to_addr=self.user.username,
            user=self.user,
            src=self.src,
            mail=mails.ARCHIVE_COPY_ERROR_USER,
            results={},
            can_change_preferences=False,
            mimetype='html',
        )
        args_desk = dict(
            to_addr=settings.OSF_SUPPORT_EMAIL,
            user=self.user,
            src=self.src,
            mail=mails.ARCHIVE_COPY_ERROR_DESK,
            results={},
            can_change_preferences=False,
            url=url,
        )
        mock_send_mail.assert_has_calls([
            call(**args_user),
            call(**args_desk),
        ], any_order=True)

    @mock.patch('website.mails.send_mail')
    def test_handle_archive_fail_size(self, mock_send_mail):
        url = settings.INTERNAL_DOMAIN + self.src._id
        archiver_utils.handle_archive_fail(
            ARCHIVER_SIZE_EXCEEDED,
            self.src,
            self.dst,
            self.user,
            {}
        )
        args_user = dict(
            to_addr=self.user.username,
            user=self.user,
            src=self.src,
            mail=mails.ARCHIVE_SIZE_EXCEEDED_USER,
            can_change_preferences=False,
            mimetype='html',
        )
        args_desk = dict(
            to_addr=settings.OSF_SUPPORT_EMAIL,
            user=self.user,
            src=self.src,
            mail=mails.ARCHIVE_SIZE_EXCEEDED_DESK,
            stat_result={},
            can_change_preferences=False,
            url=url,
        )
        mock_send_mail.assert_has_calls([
            call(**args_user),
            call(**args_desk),
        ], any_order=True)

    def test_aggregate_file_tree_metadata(self):
        a_stat_result = archiver_utils.aggregate_file_tree_metadata('dropbox', FILE_TREE, self.user)
        assert_equal(a_stat_result.disk_usage, 128 + 256)
        assert_equal(a_stat_result.num_files, 2)
        assert_equal(len(a_stat_result.targets), 2)

    @use_fake_addons
    def test_archive_provider_for(self):
        provider = self.src.get_addon(settings.ARCHIVE_PROVIDER)
        assert_equal(archiver_utils.archive_provider_for(self.src, self.user)._id, provider._id)

    @use_fake_addons
    def test_has_archive_provider(self):
        assert_true(archiver_utils.has_archive_provider(self.src, self.user))
        wo = factories.NodeFactory(creator=self.user)
        wo.delete_addon(settings.ARCHIVE_PROVIDER, auth=self.auth, _force=True)
        assert_false(archiver_utils.has_archive_provider(wo, self.user))

    @use_fake_addons
    def test_link_archive_provider(self):
        wo = factories.NodeFactory(creator=self.user)
        wo.delete_addon(settings.ARCHIVE_PROVIDER, auth=self.auth, _force=True)
        archiver_utils.link_archive_provider(wo, self.user)
        assert_true(archiver_utils.has_archive_provider(wo, self.user))

    def test_get_file_map(self):
        node = factories.NodeFactory(creator=self.user)
        file_tree = file_tree_factory(3, 3, 3)
        with mock.patch.object(BaseStorageAddon, '_get_file_tree', mock.Mock(return_value=file_tree)):
            file_map = archiver_utils.get_file_map(node)
        stack = [file_tree]
        file_map = {
            sha256: value
            for sha256, value, _ in file_map
        }
        while len(stack):
            item = stack.pop(0)
            if item['kind'] == 'file':
                sha256 = item['extra']['hashes']['sha256']
                assert_in(sha256, file_map)
                map_file = file_map[sha256]
                assert_equal(item, map_file)
            else:
                stack = stack + item['children']

    def test_get_file_map_with_components(self):
        node = factories.NodeFactory()
        comp1 = factories.NodeFactory(parent=node)
        factories.NodeFactory(parent=comp1)
        factories.NodeFactory(parent=node)

        file_tree = file_tree_factory(3, 3, 3)
        with mock.patch.object(BaseStorageAddon, '_get_file_tree', mock.Mock(return_value=file_tree)):
            file_map = archiver_utils.get_file_map(node)
            stack = [file_tree]
            file_map = {
                sha256: value
                for sha256, value, _ in file_map
            }
            while len(stack):
                item = stack.pop(0)
                if item['kind'] == 'file':
                    sha256 = item['extra']['hashes']['sha256']
                    assert_in(sha256, file_map)
                    map_file = file_map[sha256]
                    assert_equal(item, map_file)
                else:
                    stack = stack + item['children']

    def test_get_file_map_memoization(self):
        node = factories.NodeFactory()
        comp1 = factories.NodeFactory(parent=node)
        factories.NodeFactory(parent=comp1)
        factories.NodeFactory(parent=node)

        with mock.patch.object(BaseStorageAddon, '_get_file_tree') as mock_get_file_tree:
            mock_get_file_tree.return_value = file_tree_factory(3, 3, 3)

            # first call
            archiver_utils.get_file_map(node)
            call_count = mock_get_file_tree.call_count
            # second call
            archiver_utils.get_file_map(node)
            assert_equal(mock_get_file_tree.call_count, call_count)


class TestArchiverListeners(ArchiverTestCase):

    @mock.patch('website.archiver.tasks.archive')
    @mock.patch('website.archiver.utils.before_archive')
    def test_after_register(self, mock_before_archive, mock_archive):
        listeners.after_register(self.src, self.dst, self.user)
        mock_before_archive.assert_called_with(self.dst, self.user)
        mock_archive.assert_called_with(job_pk=self.archive_job._id)

    @mock.patch('website.archiver.tasks.archive')
    @mock.patch('celery.chain')
    def test_after_register_archive_runs_only_for_root(self, mock_chain, mock_archive):
        proj = factories.ProjectFactory()
        c1 = factories.ProjectFactory(parent=proj)
        c2 = factories.ProjectFactory(parent=c1)
        reg = factories.RegistrationFactory(project=proj)
        rc1 = reg.nodes[0]
        rc2 = rc1.nodes[0]
        mock_chain.reset_mock()
        listeners.after_register(c1, rc1, self.user)
        assert_false(mock_chain.called)
        listeners.after_register(c2, rc2, self.user)
        assert_false(mock_chain.called)
        listeners.after_register(proj, reg, self.user)
        for kwargs in [dict(job_pk=n.archive_job._id,) for n in [reg, rc1, rc2]]:
            mock_archive.assert_any_call(**kwargs)

    @mock.patch('website.archiver.tasks.archive')
    @mock.patch('celery.chain')
    def test_after_register_does_not_archive_pointers(self, mock_chain, mock_archive):
        proj = factories.ProjectFactory(creator=self.user)
        c1 = factories.ProjectFactory(creator=self.user, parent=proj)
        other = factories.ProjectFactory(creator=self.user)
        reg = factories.RegistrationFactory(project=proj)
        r1 = reg._nodes.first()
        proj.add_pointer(other, auth=Auth(self.user))
        listeners.after_register(c1, r1, self.user)
        listeners.after_register(proj, reg, self.user)
        for kwargs in [dict(job_pk=n.archive_job._id,) for n in [reg, r1]]:
            mock_archive.assert_any_call(**kwargs)

    @mock.patch('website.archiver.tasks.archive_success.delay')
    def test_archive_callback_pending(self, mock_delay):
        self.archive_job.update_target(
            'osfstorage',
            ARCHIVER_INITIATED
        )
        self.dst.archive_job.update_target(
            'osfstorage',
            ARCHIVER_SUCCESS
        )
        self.dst.archive_job.save()
        with mock.patch('website.mails.send_mail') as mock_send:
            with mock.patch('website.archiver.utils.handle_archive_fail') as mock_fail:
                listeners.archive_callback(self.dst)
        assert_false(mock_send.called)
        assert_false(mock_fail.called)
        assert_true(mock_delay.called)

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.archiver.tasks.archive_success.delay')
    def test_archive_callback_done_success(self, mock_send, mock_archive_success):
        self.dst.archive_job.update_target('osfstorage', ARCHIVER_SUCCESS)
        self.dst.archive_job.save()
        listeners.archive_callback(self.dst)
        assert_equal(mock_send.call_count, 1)

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.archiver.tasks.archive_success.delay')
    def test_archive_callback_done_embargoed(self, mock_send, mock_archive_success):
        end_date = timezone.now() + datetime.timedelta(days=30)
        self.dst.archive_job.meta = {
            'embargo_urls': {
                contrib._id: None
                for contrib in self.dst.contributors
            }
        }
        self.dst.embargo_registration(self.user, end_date)
        self.dst.archive_job.update_target('osfstorage', ARCHIVER_SUCCESS)
        self.dst.save()
        listeners.archive_callback(self.dst)
        assert_equal(mock_send.call_count, 1)

    def test_archive_callback_done_errors(self):
        self.dst.archive_job.update_target('osfstorage', ARCHIVER_FAILURE)
        self.dst.archive_job.save()
        with mock.patch('website.archiver.utils.handle_archive_fail') as mock_fail:
            listeners.archive_callback(self.dst)
        call_args = mock_fail.call_args[0]
        assert call_args[0] == ARCHIVER_UNCAUGHT_ERROR
        assert call_args[1] == self.src
        assert call_args[2] == self.dst
        assert call_args[3] == self.user
        assert call_args[3] == self.user
        assert list(call_args[4]) == list(self.dst.archive_job.target_addons.all())

    def test_archive_callback_updates_archiving_state_when_done(self):
        proj = factories.NodeFactory()
        factories.NodeFactory(parent=proj)
        reg = factories.RegistrationFactory(project=proj)
        reg.archive_job.update_target('osfstorage', ARCHIVER_INITIATED)
        child = reg.nodes[0]
        child.archive_job.update_target('osfstorage', ARCHIVER_SUCCESS)
        child.save()
        listeners.archive_callback(child)
        assert_false(child.archiving)

    def test_archive_tree_finished_d1(self):
        self.dst.archive_job.update_target('osfstorage', ARCHIVER_SUCCESS)
        self.dst.save()
        assert_true(self.dst.archive_job.archive_tree_finished())

    def test_archive_tree_finished_d3(self):
        proj = factories.NodeFactory()
        child = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=child)
        reg = factories.RegistrationFactory(project=proj)
        rchild = reg._nodes.first()
        rchild2 = rchild._nodes.first()
        for node in [reg, rchild, rchild2]:
            node.archive_job._set_target('osfstorage')
        for node in [reg, rchild, rchild2]:
            node.archive_job.update_target('osfstorage', ARCHIVER_SUCCESS)
        for node in [reg, rchild, rchild2]:
            assert_true(node.archive_job.archive_tree_finished())

    def test_archive_tree_finished_false(self):
        proj = factories.NodeFactory()
        child = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=child)
        reg = factories.RegistrationFactory(project=proj)
        rchild = reg._nodes.first()
        rchild2 = rchild._nodes.first()
        for node in [reg, rchild, rchild2]:
            node.archive_job._set_target('osfstorage')
        for node in [reg, rchild]:
            node.archive_job.update_target('osfstorage', ARCHIVER_SUCCESS)
        rchild2.archive_job.update_target('osfstorage', ARCHIVER_INITIATED)
        rchild2.save()
        for node in [reg, rchild, rchild2]:
            assert_false(node.archive_job.archive_tree_finished())

    def test_archive_tree_finished_false_for_partial_archive(self):
        proj = factories.NodeFactory()
        child = factories.NodeFactory(parent=proj, title='child')
        sibling = factories.NodeFactory(parent=proj, title='sibling')

        reg = factories.RegistrationFactory(project=proj)
        rchild = reg._nodes.filter(title='child').get()
        rsibling = reg._nodes.filter(title='sibling').get()
        for node in [reg, rchild, rsibling]:
            node.archive_job._set_target('osfstorage')
        for node in [reg, rchild]:
            node.archive_job.update_target('osfstorage', ARCHIVER_SUCCESS)
        rsibling.archive_job.update_target('osfstorage', ARCHIVER_INITIATED)
        rsibling.save()
        assert_false(reg.archive_job.archive_tree_finished())

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.archiver.tasks.archive_success.delay')
    def test_archive_callback_on_tree_sends_only_one_email(self, mock_send_success, mock_arhive_success):
        proj = factories.NodeFactory()
        child = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=child)
        reg = factories.RegistrationFactory(project=proj)
        rchild = reg._nodes.first()
        rchild2 = rchild._nodes.first()
        for node in [reg, rchild, rchild2]:
            node.archive_job._set_target('osfstorage')
        for node in [reg, rchild, rchild2]:
            node.archive_job.update_target('osfstorage', ARCHIVER_INITIATED)
        rchild.archive_job.update_target('osfstorage', ARCHIVER_SUCCESS)
        rchild.save()
        listeners.archive_callback(rchild)
        assert_false(mock_send_success.called)
        reg.archive_job.update_target('osfstorage', ARCHIVER_SUCCESS)
        reg.save()
        listeners.archive_callback(reg)
        assert_false(mock_send_success.called)
        rchild2.archive_job.update_target('osfstorage', ARCHIVER_SUCCESS)
        rchild2.save()
        listeners.archive_callback(rchild2)
        assert_equal(mock_send_success.call_count, 1)
        assert_true(mock_send_success.called)

class TestArchiverScripts(ArchiverTestCase):

    def test_find_failed_registrations(self):
        failures = []
        legacy = []
        delta = settings.ARCHIVE_TIMEOUT_TIMEDELTA + datetime.timedelta(hours=1)
        for i in range(5):
            reg = factories.RegistrationFactory()
            archive_job = reg.archive_job
            archive_job.datetime_initiated = timezone.now() - delta
            archive_job.save()
            reg.save()
            ArchiveJob.delete(archive_job)
            legacy.append(reg._id)
        for i in range(5):
            reg = factories.RegistrationFactory()
            datetime_initiated = timezone.now() - delta
            archive_job = reg.archive_job
            archive_job.datetime_initiated = datetime_initiated
            archive_job.status = ARCHIVER_INITIATED
            archive_job.save()
            reg.save()
            archive_job._set_target('osfstorage')
            archive_job.update_target('osfstorage', ARCHIVER_INITIATED)
            archive_job.sent = False
            archive_job.save()
            failures.append(reg._id)
        pending = []
        for i in range(5):
            reg = factories.RegistrationFactory()
            archive_job = reg.archive_job
            archive_job._set_target('osfstorage')
            archive_job.update_target('osfstorage', ARCHIVER_INITIATED)
            archive_job.save()
            pending.append(reg)
        failed = Registration.find_failed_registrations()
        assert_equal(len(failed), 5)
        assert_items_equal([f._id for f in failed], failures)
        for pk in legacy:
            assert_false(pk in failed)


class TestArchiverDecorators(ArchiverTestCase):

    @mock.patch('website.archiver.signals.archive_fail.send')
    def test_fail_archive_on_error(self, mock_fail):
        e = HTTPError(418)
        def error(*args, **kwargs):
            raise e

        func = fail_archive_on_error(error)
        func(node=self.dst)
        mock_fail.assert_called_with(
            self.dst,
            errors=[e.message]
        )

class TestArchiverBehavior(OsfTestCase):

    @mock.patch('osf.models.AbstractNode.update_search')
    def test_archiving_registrations_not_added_to_search_before_archival(self, mock_update_search):
        proj = factories.ProjectFactory()
        reg = factories.RegistrationFactory(project=proj)
        reg.save()
        assert_false(mock_update_search.called)

    @mock.patch('osf.models.AbstractNode.update_search')
    @mock.patch('website.mails.send_mail')
    @mock.patch('website.archiver.tasks.archive_success.delay')
    def test_archiving_nodes_added_to_search_on_archive_success_if_public(self, mock_update_search, mock_send, mock_archive_success):
        proj = factories.ProjectFactory()
        reg = factories.RegistrationFactory(project=proj)
        reg.save()
        with nested(
            mock.patch('osf.models.ArchiveJob.archive_tree_finished', mock.Mock(return_value=True)),
            mock.patch('osf.models.ArchiveJob.success', mock.PropertyMock(return_value=True))
        ) as (mock_finished, mock_success):
            listeners.archive_callback(reg)
        assert_equal(mock_update_search.call_count, 1)

    @pytest.mark.enable_search
    @mock.patch('website.search.elastic_search.delete_doc')
    @mock.patch('website.mails.send_mail')
    def test_archiving_nodes_not_added_to_search_on_archive_failure(self, mock_send, mock_delete_index_node):
        proj = factories.ProjectFactory()
        reg = factories.RegistrationFactory(project=proj, archive=True)
        reg.save()
        with nested(
                mock.patch('osf.models.archive.ArchiveJob.archive_tree_finished', mock.Mock(return_value=True)),
                mock.patch('osf.models.archive.ArchiveJob.success', mock.PropertyMock(return_value=False))
        ) as (mock_finished, mock_success):
            listeners.archive_callback(reg)
        assert_true(mock_delete_index_node.called)

    @mock.patch('osf.models.AbstractNode.update_search')
    @mock.patch('website.mails.send_mail')
    def test_archiving_nodes_not_added_to_search_on_archive_incomplete(self, mock_send, mock_update_search):
        proj = factories.ProjectFactory()
        reg = factories.RegistrationFactory(project=proj)
        reg.save()
        with mock.patch('osf.models.ArchiveJob.archive_tree_finished', mock.Mock(return_value=False)):
            listeners.archive_callback(reg)
        assert_false(mock_update_search.called)


class TestArchiveTarget(OsfTestCase):

    def test_repr(self):
        target = ArchiveTarget()
        result = repr(target)
        assert_in('ArchiveTarget', result)
        assert_in(str(target._id), result)


class TestArchiveJobModel(OsfTestCase):

    def tearDown(self, *args, **kwargs):
        super(TestArchiveJobModel, self).tearDown(*args, **kwargs)
        with open(os.path.join(settings.ROOT, 'addons.json')) as fp:
            addon_settings = json.load(fp)
            settings.ADDONS_ARCHIVABLE = addon_settings['addons_archivable']

    def test_repr(self):
        job = ArchiveJob()
        result = repr(job)
        assert_in('ArchiveJob', result)
        assert_in(str(job.done), result)
        assert_in(str(job._id), result)

    def test_target_info(self):
        target = ArchiveTarget(name='neon-archive')
        target.save()
        job = factories.ArchiveJobFactory()
        job.target_addons.add(target)

        result = job.target_info()
        assert_equal(len(result), 1)

        item = result[0]

        assert_equal(item['name'], target.name)
        assert_equal(item['status'], target.status)
        assert_equal(item['stat_result'], target.stat_result)
        assert_equal(item['errors'], target.errors)

    def test_get_target(self):
        proj = factories.ProjectFactory()
        reg = factories.RegistrationFactory(project=proj)
        job = ArchiveJob.objects.create(src_node=proj, dst_node=reg, initiator=proj.creator)
        job.set_targets()
        osfstorage = job.get_target('osfstorage')
        assert_false(not osfstorage)
        none = job.get_target('fake')
        assert_false(none)

    def test_set_targets(self):
        proj = factories.ProjectFactory()
        reg = factories.RegistrationFactory(project=proj)
        job = ArchiveJob(src_node=proj, dst_node=reg, initiator=proj.creator)
        job.save()
        job.set_targets()

        assert_equal(list(job.target_addons.values_list('name', flat=True)), ['osfstorage'])

    def test_archive_tree_finished_with_nodes(self):
        proj = factories.NodeFactory()
        factories.NodeFactory(parent=proj)
        comp2 = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=comp2)
        reg = factories.RegistrationFactory(project=proj)
        rchild1 = reg._nodes.first()
        for node in reg.node_and_primary_descendants():
            assert_false(node.archive_job.archive_tree_finished())

        for target in rchild1.archive_job.target_addons.all():
            rchild1.archive_job.update_target(target.name, ARCHIVER_SUCCESS)
            rchild1.archive_job.save()

        assert_false(reg.archive_job.archive_tree_finished())

        for node in reg.node_and_primary_descendants():
            for target in node.archive_job.target_addons.all():
                node.archive_job.update_target(target.name, ARCHIVER_SUCCESS)
        for node in reg.node_and_primary_descendants():
            assert_true(node.archive_job.archive_tree_finished())

# Regression test for https://openscience.atlassian.net/browse/OSF-9085
def test_archiver_uncaught_error_mail_renders():
    src = factories.ProjectFactory()
    user = src.creator
    job = factories.ArchiveJobFactory()
    mail = mails.ARCHIVE_UNCAUGHT_ERROR_DESK
    assert mail.html(
        user=user,
        src=src,
        results=job.target_addons.all(),
        url=settings.INTERNAL_DOMAIN + src._id,
        can_change_preferences=False,
    )
