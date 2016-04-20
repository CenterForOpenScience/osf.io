#-*- coding: utf-8 -*-
import datetime
import functools
import json
import logging
import itertools
import random
import copy
import re

import celery
import mock  # noqa
from contextlib import nested
from mock import call
from nose.tools import *  # noqa PEP8 asserts
import httpretty
from modularodm import Q

from scripts import cleanup_failed_registrations as scripts

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
from website.app import *  # noqa
from website.archiver import listeners
from website.archiver.tasks import *   # noqa
from website.archiver.model import ArchiveTarget, ArchiveJob
from website.archiver.decorators import fail_archive_on_error

from website import mails
from website import settings
from website.util import waterbutler_url_for
from website.project.model import Node, NodeLog, ensure_schemas, MetaSchema
from website.addons.base import StorageAddonBase

from tests import factories
from tests.base import OsfTestCase, fake
from tests import utils as test_utils

from tests.utils import unique as _unique


SILENT_LOGGERS = (
    'framework.celery_tasks.utils',
    'website.archiver.tasks',
)
for each in SILENT_LOGGERS:
    logging.getLogger(each).setLevel(logging.CRITICAL)

sha256_factory = _unique(fake.sha256)
name_factory = _unique(fake.word)

def file_factory(sha256=None):
    fname = name_factory()
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

class MockAddon(mock.MagicMock, StorageAddonBase):

    complete = True

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
            mock.patch('framework.addons.AddonModelMixin.add_addon', mock.Mock(side_effect=_mock_get_or_add)),
            mock.patch('framework.addons.AddonModelMixin.get_addon', mock.Mock(side_effect=_mock_get_addon)),
            mock.patch('framework.addons.AddonModelMixin.delete_addon', mock.Mock(side_effect=_mock_delete_addon)),
            mock.patch('framework.addons.AddonModelMixin.get_or_add_addon', mock.Mock(side_effect=_mock_get_or_add))
        ):
            ret = func(*args, **kwargs)
            active_addons = {'osfstorage', 'dropbox'}
            return ret
    return wrapper

class ArchiverTestCase(OsfTestCase):

    @use_fake_addons
    def setUp(self):
        super(ArchiverTestCase, self).setUp()

        handlers.celery_before_request()
        self.user = factories.UserFactory()
        self.auth = Auth(user=self.user)
        self.src = factories.NodeFactory(creator=self.user)
        self.dst = factories.RegistrationFactory(user=self.user, project=self.src, send_signals=False)
        archiver_utils.before_archive(self.dst, self.user)
        self.archive_job = self.dst.archive_job

class TestStorageAddonBase(ArchiverTestCase):

    RESP_MAP = {
        '/': dict(data=FILE_TREE['children']),
        '/1234567': dict(data=FILE_TREE['children'][0]),
        '/qwerty': dict(data=FILE_TREE['children'][1]['children']),
        '/qwerty/asdfgh': dict(data=FILE_TREE['children'][1]['children'][0]),
    }

    @httpretty.activate
    def _test__get_file_tree(self, addon_short_name):
        requests_made = []
        def callback(request, uri, headers):
            path = request.querystring['path'][0]
            requests_made.append(path)
            return (200, headers, json.dumps(self.RESP_MAP[path]))

        for path in self.RESP_MAP.keys():
            url = waterbutler_url_for(
                'metadata',
                provider=addon_short_name,
                path=path,
                node=self.src,
                user=self.user,
                view_only=True,
            )
            httpretty.register_uri(httpretty.GET,
                                   url,
                                   body=callback,
                                   content_type='applcation/json')
        addon = self.src.get_or_add_addon(addon_short_name, auth=self.auth)
        root = {
            'path': '/',
            'name': '',
            'kind': 'folder',
        }
        file_tree = addon._get_file_tree(root, self.user)
        assert_equal(FILE_TREE, file_tree)
        assert_equal(requests_made, ['/', '/qwerty'])  # no requests made for files

    def _test_addon(self, addon_short_name):
        self._test__get_file_tree(addon_short_name)

    def test_addons(self):
        #  Test that each addon in settings.ADDONS_ARCHIVABLE other than wiki implementes the StorageAddonBase interface
        for addon in [a for a in settings.ADDONS_ARCHIVABLE if a not in ['wiki']]:
            self._test_addon(addon)

class TestArchiverTasks(ArchiverTestCase):

    @use_fake_addons
    @mock.patch('framework.celery_tasks.handlers.enqueue_task')
    @mock.patch('celery.chain')
    def test_archive(self, mock_chain, mock_enqueue):
        archive(job_pk=self.archive_job._id)
        targets = [self.src.get_addon(name) for name in settings.ADDONS_ARCHIVABLE]
        target_addons = [addon for addon in targets if (addon and addon.complete and isinstance(addon, StorageAddonBase))]
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

    @use_fake_addons
    def test_stat_addon(self):
        res = stat_addon('dropbox', self.archive_job._id)
        assert_equal(res.target_name, 'dropbox')
        assert_equal(res.disk_usage, 128 + 256)

    @use_fake_addons
    @mock.patch('website.archiver.tasks.archive_addon.delay')
    def test_archive_node_pass(self, mock_archive_addon):
        settings.MAX_ARCHIVE_SIZE = 1024 ** 3
        with mock.patch.object(StorageAddonBase, '_get_file_tree') as mock_file_tree:
            mock_file_tree.return_value = FILE_TREE
            results = [stat_addon(addon, self.archive_job._id) for addon in ['osfstorage', 'dropbox']]
        with mock.patch.object(celery, 'group') as mock_group:
            archive_node(results, self.archive_job._id)
        archive_dropbox_signature = archive_addon.si(
            'dropbox',
            self.archive_job._id,
            results
        )
        assert(mock_group.called_with(archive_dropbox_signature))

    @use_fake_addons
    def test_archive_node_fail(self):
        settings.MAX_ARCHIVE_SIZE = 100
        results = [stat_addon(addon, self.archive_job._id) for addon in ['osfstorage', 'dropbox']]
        with mock.patch('website.archiver.tasks.ArchiverTask.on_failure') as mock_fail:
            try:
                archive_node.apply(args=(results, self.archive_job._id))
            except:
                pass
        assert_true(isinstance(mock_fail.call_args[0][0], ArchiverSizeExceeded))

    @mock.patch('website.archiver.tasks.archive_addon.delay')
    def test_archive_node_does_not_archive_empty_addons(self, mock_archive_addon):
        with mock.patch.object(self.src, 'get_addon') as mock_get_addon:
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
        mock_archive_addon.assert_not_called()

    @use_fake_addons
    @mock.patch('website.archiver.tasks.archive_addon.delay')
    def test_archive_node_no_archive_size_limit(self, mock_archive_addon):
        settings.MAX_ARCHIVE_SIZE = 100
        self.archive_job.initiator.system_tags.append(NO_ARCHIVE_LIMIT)
        self.archive_job.initiator.save()
        with mock.patch.object(StorageAddonBase, '_get_file_tree') as mock_file_tree:
            mock_file_tree.return_value = FILE_TREE
            results = [stat_addon(addon, self.archive_job._id) for addon in ['osfstorage', 'dropbox']]
        with mock.patch.object(celery, 'group') as mock_group:
            archive_node(results, self.archive_job._id)
        archive_dropbox_signature = archive_addon.si(
            'dropbox',
            self.archive_job._id,
            results
        )
        assert(mock_group.called_with(archive_dropbox_signature))

    @use_fake_addons
    @mock.patch('website.archiver.tasks.make_copy_request.delay')
    def test_archive_addon(self, mock_make_copy_request):
        result = archiver_utils.aggregate_file_tree_metadata('dropbox', FILE_TREE, self.user)
        archive_addon('dropbox', self.archive_job._id, result)
        assert_equal(self.archive_job.get_target('dropbox').status, ARCHIVER_INITIATED)
        cookie = self.user.get_or_create_cookie()
        assert(mock_make_copy_request.called_with(
            self.archive_job._id,
            settings.WATERBUTLER_URL + '/ops/copy',
            data=dict(
                source=dict(
                    cookie=cookie,
                    nid=self.src._id,
                    provider='dropbox',
                    path='/',
                ),
                destination=dict(
                    cookie=cookie,
                    nid=self.dst._id,
                    provider=settings.ARCHIVE_PROVIDER,
                    path='/',
                ),
                rename='Archive of DropBox',
            )
        ))

    def test_archive_success(self):
        ensure_schemas()
        file_tree = file_tree_factory(3, 3, 3)
        selected_files = select_files_from_tree(file_tree)

        node = factories.NodeFactory(creator=self.user)
        prereg_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )
        data = {
            ('q_' + selected_file['name']): {
                'value': fake.word(),
                'extra': {
                    'selectedFileName': selected_file['name'],
                    'nodeId': node._id,
                    'sha256': sha256,
                    'viewUrl': '/project/{0}/files/osfstorage{1}'.format(node._id, selected_file['path'])
                }
            }
            for sha256, selected_file in selected_files.items()
        }
        object_types = {
            ('q_' + selected_file['name'] + '_obj'): {
                'value': {
                    name_factory(): {
                        'value': fake.word(),
                        'extra': {
                            'selectedFileName': selected_file['name'],
                            'nodeId': node._id,
                            'sha256': sha256,
                            'viewUrl': '/project/{0}/files/osfstorage{1}'.format(node._id, selected_file['path'])
                        }
                    },
                    name_factory(): {
                        'value': fake.word()
                    }
                }
            }
            for sha256, selected_file in selected_files.items()
        }
        data.update(copy.deepcopy(object_types))
        other_questions = {
            'q{}'.format(i): {
                'value': fake.word()
            }
            for i in range(5)
        }
        data.update(other_questions)

        with test_utils.mock_archive(node, schema=prereg_schema, data=data, autocomplete=True, autoapprove=True) as registration:
            with mock.patch.object(StorageAddonBase, '_get_file_tree', mock.Mock(return_value=file_tree)):
                job = factories.ArchiveJobFactory()
                archive_success(registration._id, job._id)
                for key, question in registration.registered_meta[prereg_schema._id].items():
                    target = None
                    if isinstance(question['value'], dict):
                        target = [v for v in question['value'].values() if 'extra' in v and 'sha256' in v['extra']][0]
                    elif 'extra' in question and 'hashes' in question['extra']:
                        target = question

                    if target:
                        assert_in(registration._id, target['extra']['viewUrl'])
                        assert_not_in(node._id, target['extra']['viewUrl'])
                        del selected_files[target['extra']['sha256']]
                    else:
                        # check non-file questions are unmodified
                        assert_equal(data[key]['value'], question['value'])
                assert_false(selected_files)

    def test_archive_success_with_components(self):
        ensure_schemas()
        node = factories.NodeFactory(creator=self.user)
        comp1 = factories.NodeFactory(parent=node, creator=self.user)
        factories.NodeFactory(parent=comp1, creator=self.user)
        factories.NodeFactory(parent=node, creator=self.user)
        nodes = [n for n in node.node_and_primary_descendants()]

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

        prereg_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )
        data = {
            ('q_' + selected_file['name']): {
                'value': fake.word(),
                'extra': {
                    'sha256': sha256,
                    'viewUrl': '/project/{0}/files/osfstorage{1}'.format(
                        selected_file_node_index[sha256],
                        selected_file['path']
                    ),
                    'selectedFileName': selected_file['name'],
                    'nodeId': selected_file_node_index[sha256]
                }
            }
            for sha256, selected_file in selected_files.items()
        }
        object_types = {
            ('q_' + selected_file['name'] + '_obj'): {
                'value': {
                    name_factory(): {
                        'value': fake.word(),
                        'extra': {
                            'sha256': sha256,
                            'viewUrl': '/project/{0}/files/osfstorage{1}'.format(
                                selected_file_node_index[sha256],
                                selected_file['path']
                            ),
                            'selectedFileName': selected_file['name'],
                            'nodeId': selected_file_node_index[sha256]
                        }
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

        with test_utils.mock_archive(node, schema=prereg_schema, data=copy.deepcopy(data), autocomplete=True, autoapprove=True) as registration:
            patches = []
            for n in registration.node_and_primary_descendants():
                file_tree = file_trees[n.registered_from._id]
                osfstorage = n.get_addon('osfstorage')
                patch = mock.patch.object(
                    osfstorage,
                    '_get_file_tree',
                    mock.Mock(return_value=file_tree)
                )
                patch.start()
                patches.append(patch)
                n_patch = mock.patch.object(
                    n,
                    'get_addon',
                    mock.Mock(return_value=osfstorage)
                )
                n_patch.start()
                patches.append(n_patch)
            job = factories.ArchiveJobFactory()
            archive_success(registration._id, job._id)

            for key, question in registration.registered_meta[prereg_schema._id].items():
                target = None
                if isinstance(question['value'], dict):
                    target = [v for v in question['value'].values() if 'extra' in v and 'sha256' in v['extra']][0]
                elif 'extra' in question and 'sha256' in question['extra']:
                    target = question

                if target:
                    node_id = re.search(
                        r'^/project/(?P<node_id>\w{5}).+$',
                        target['extra']['viewUrl']
                    ).groupdict()['node_id']
                    assert_in(
                        node_id,
                        [r._id for r in registration.node_and_primary_descendants()]
                    )
                    if target['extra']['sha256'] in selected_files:
                        del selected_files[target['extra']['sha256']]
                else:
                    # check non-file questions are unmodified
                    assert_equal(data[key]['value'], question['value'])
            # ensure each selected file was checked
            assert_false(selected_files)

            for patch in patches:
                patch.stop()

    def test_archive_success_different_name_same_sha(self):
        ensure_schemas()
        file_tree = file_tree_factory(0, 0, 0)
        fake_file = file_factory()
        fake_file2 = file_factory(sha256=fake_file['extra']['hashes']['sha256'])
        file_tree['children'] = [fake_file, fake_file2]

        node = factories.NodeFactory(creator=self.user)
        prereg_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )
        data = {
            ('q_' + fake_file['name']): {
                'value': fake.word(),
                'extra': {
                    'sha256': fake_file['extra']['hashes']['sha256'],
                    'viewUrl': '/project/{0}/files/osfstorage{1}'.format(
                        node._id,
                        fake_file['path']
                    ),
                    'selectedFileName': fake_file['name'],
                    'nodeId': node._id
                }
            }
        }

        with test_utils.mock_archive(node, schema=prereg_schema, data=data, autocomplete=True, autoapprove=True) as registration:
            with mock.patch.object(StorageAddonBase, '_get_file_tree', mock.Mock(return_value=file_tree)):
                job = factories.ArchiveJobFactory()
                archive_success(registration._id, job._id)
                for key, question in registration.registered_meta[prereg_schema._id].items():
                    assert_equal(question['extra']['selectedFileName'], fake_file['name'])

    def test_archive_success_same_file_in_component(self):
        ensure_schemas()
        file_tree = file_tree_factory(3, 3, 3)
        selected = select_files_from_tree(file_tree).values()[0]

        child_file_tree = file_tree_factory(0, 0, 0)
        child_file_tree['children'] = [selected]

        node = factories.NodeFactory(creator=self.user)
        child = factories.NodeFactory(creator=self.user, parent=node)

        prereg_schema = MetaSchema.find_one(
            Q('name', 'eq', 'Prereg Challenge') &
            Q('schema_version', 'eq', 2)
        )
        data = {
            ('q_' + selected['name']): {
                'value': fake.word(),
                'extra': {
                    'sha256': selected['extra']['hashes']['sha256'],
                    'viewUrl': '/project/{0}/files/osfstorage{1}'.format(
                        child._id,
                        selected['path']
                    ),
                    'selectedFileName': selected['name'],
                    'nodeId': child._id
                }
            }
        }

        with test_utils.mock_archive(node, schema=prereg_schema, data=data, autocomplete=True, autoapprove=True) as registration:
            with mock.patch.object(StorageAddonBase, '_get_file_tree', mock.Mock(return_value=file_tree)):
                job = factories.ArchiveJobFactory()
                archive_success(registration._id, job._id)
                child_reg = registration.nodes[0]
                for key, question in registration.registered_meta[prereg_schema._id].items():
                    assert_in(child_reg._id, question['extra']['viewUrl'])


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
            to_addr=settings.SUPPORT_EMAIL,
            user=self.user,
            src=self.src,
            mail=mails.ARCHIVE_COPY_ERROR_DESK,
            results={},
        )
        mock_send_mail.assert_has_calls([
            call(**args_user),
            call(**args_desk),
        ], any_order=True)

    @mock.patch('website.mails.send_mail')
    def test_handle_archive_fail_size(self, mock_send_mail):
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
            to_addr=settings.SUPPORT_EMAIL,
            user=self.user,
            src=self.src,
            mail=mails.ARCHIVE_SIZE_EXCEEDED_DESK,
            stat_result={},
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
        wo = factories.NodeFactory(user=self.user)
        wo.delete_addon(settings.ARCHIVE_PROVIDER, auth=self.auth, _force=True)
        assert_false(archiver_utils.has_archive_provider(wo, self.user))

    @use_fake_addons
    def test_link_archive_provider(self):
        wo = factories.NodeFactory(user=self.user)
        wo.delete_addon(settings.ARCHIVE_PROVIDER, auth=self.auth, _force=True)
        archiver_utils.link_archive_provider(wo, self.user)
        assert_true(archiver_utils.has_archive_provider(wo, self.user))

    def test_get_file_map(self):
        node = factories.NodeFactory(creator=self.user)
        file_tree = file_tree_factory(3, 3, 3)
        with mock.patch.object(StorageAddonBase, '_get_file_tree', mock.Mock(return_value=file_tree)):
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
        comp1a = factories.NodeFactory(parent=comp1)
        comp2 = factories.NodeFactory(parent=node)

        file_trees = {
            n._id: file_tree_factory(3, 3, 3)
            for n in [node, comp1, comp1a, comp2]
        }

        patches = []
        for n in [node, comp1, comp1a, comp2]:
            file_tree = file_trees[n._id]
            osfstorage = n.get_addon('osfstorage')
            patch = mock.patch.object(osfstorage, '_get_file_tree', mock.Mock(return_value=file_tree))
            patch.start()
            patches.append(patch)
            n_patch = mock.patch.object(
                n,
                'get_addon',
                mock.Mock(return_value=osfstorage)
            )
            n_patch.start()
            patches.append(n_patch)

        file_map = archiver_utils.get_file_map(node)
        stack = file_trees.values()
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

        for patch in patches:
            patch.stop()

    def test_get_file_map_memoization(self):
        node = factories.NodeFactory()
        comp1 = factories.NodeFactory(parent=node)
        comp1a = factories.NodeFactory(parent=comp1)
        comp2 = factories.NodeFactory(parent=node)

        file_trees = {
            n._id: file_tree_factory(3, 3, 3)
            for n in [node, comp1, comp1a, comp2]
        }
        patches = {}
        mocks = {}
        for n in [node, comp1, comp1a, comp2]:
            file_tree = file_trees[n._id]
            osfstorage = n.get_addon('osfstorage')
            mocked = mock.Mock(return_value=file_tree)
            patch = mock.patch.object(osfstorage, '_get_file_tree', mocked)
            patch.start()
            patches[n._id] = patch
            mocks[n._id] = mocked
            n_patch = mock.patch.object(
                n,
                'get_addon',
                mock.Mock(return_value=osfstorage)
            )
            n_patch.start()
            patches[osfstorage._id] = n_patch

        # first call
        file_map = archiver_utils.get_file_map(node)
        file_map = {
            sha256: value
            for sha256, value, _ in file_map
        }
        for mocked in mocks.values():
            mocked.assert_called_once()
        # second call
        file_map = archiver_utils.get_file_map(node)
        file_map = {
            sha256: value
            for sha256, value, _ in file_map
        }
        for mocked in mocks.values():
            mocked.assert_called_once()
        for patch in patches.values():
            patch.stop()


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
        listeners.after_register(c1, rc1, self.user)
        mock_chain.assert_not_called()
        listeners.after_register(c2, rc2, self.user)
        mock_chain.assert_not_called()
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
        r1 = reg.nodes[0]
        proj.add_pointer(other, auth=Auth(self.user))
        listeners.after_register(c1, r1, self.user)
        listeners.after_register(proj, reg, self.user)
        for kwargs in [dict(job_pk=n.archive_job._id,) for n in [reg, r1]]:
            mock_archive.assert_any_call(**kwargs)

    def test_archive_callback_pending(self):
        for addon in ['osfstorage', 'dropbox']:
            self.archive_job.update_target(
                addon,
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

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.archiver.tasks.archive_success.delay')
    def test_archive_callback_done_success(self, mock_send, mock_archive_success):
        for addon in ['osfstorage', 'dropbox']:
            self.dst.archive_job.update_target(addon, ARCHIVER_SUCCESS)
        self.dst.archive_job.save()
        listeners.archive_callback(self.dst)
        mock_send.assert_called()

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.archiver.tasks.archive_success.delay')
    def test_archive_callback_done_embargoed(self, mock_send, mock_archive_success):
        end_date = datetime.datetime.now() + datetime.timedelta(days=30)
        self.dst.archive_job.meta = {
            'embargo_urls': {
                contrib._id: None
                for contrib in self.dst.contributors
            }
        }
        self.dst.embargo_registration(self.user, end_date)
        for addon in ['osfstorage', 'dropbox']:
            self.dst.archive_job.update_target(addon, ARCHIVER_SUCCESS)
        self.dst.save()
        listeners.archive_callback(self.dst)
        mock_send.assert_called()

    def test_archive_callback_done_errors(self):
        self.dst.archive_job.update_target('dropbox', ARCHIVER_SUCCESS)
        self.dst.archive_job.update_target('osfstorage', ARCHIVER_FAILURE)
        self.dst.archive_job.save()
        with mock.patch('website.archiver.utils.handle_archive_fail') as mock_fail:
            listeners.archive_callback(self.dst)
        assert(mock_fail.called_with(ARCHIVER_NETWORK_ERROR, self.src, self.dst, self.user, self.dst.archive_job.target_addons))

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
        for addon in ['osfstorage', 'dropbox']:
            self.dst.archive_job.update_target(addon, ARCHIVER_SUCCESS)
        self.dst.save()
        assert_true(self.dst.archive_job.archive_tree_finished())

    def test_archive_tree_finished_d3(self):
        proj = factories.NodeFactory()
        child = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=child)
        reg = factories.RegistrationFactory(project=proj)
        rchild = reg.nodes[0]
        rchild2 = rchild.nodes[0]
        for node in [reg, rchild, rchild2]:
            for addon in ['osfstorage', 'dropbox']:
                node.archive_job._set_target(addon)
        for node in [reg, rchild, rchild2]:
            for addon in ['osfstorage', 'dropbox']:
                node.archive_job.update_target(addon, ARCHIVER_SUCCESS)
        for node in [reg, rchild, rchild2]:
            assert_true(node.archive_job.archive_tree_finished())

    def test_archive_tree_finished_false(self):
        proj = factories.NodeFactory()
        child = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=child)
        reg = factories.RegistrationFactory(project=proj)
        rchild = reg.nodes[0]
        rchild2 = rchild.nodes[0]
        for node in [reg, rchild, rchild2]:
            for addon in ['dropbox', 'osfstorage']:
                node.archive_job._set_target(addon)
        for node in [reg, rchild]:
            for addon in ['dropbox', 'osfstorage']:
                node.archive_job.update_target(addon, ARCHIVER_SUCCESS)
        for addon in ['dropbox', 'osfstorage']:
            rchild2.archive_job.update_target(addon, ARCHIVER_INITIATED)
        rchild2.save()
        for node in [reg, rchild, rchild2]:
            assert_false(node.archive_job.archive_tree_finished())

    @mock.patch('website.mails.send_mail')
    @mock.patch('website.archiver.tasks.archive_success.delay')
    def test_archive_callback_on_tree_sends_only_one_email(self, mock_send_success, mock_arhive_success):
        proj = factories.NodeFactory()
        child = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=child)
        reg = factories.RegistrationFactory(project=proj)
        rchild = reg.nodes[0]
        rchild2 = rchild.nodes[0]
        for node in [reg, rchild, rchild2]:
            for addon in ['dropbox', 'osfstorage']:
                node.archive_job._set_target(addon)
        for node in [reg, rchild, rchild2]:
            for addon in ['dropbox', 'osfstorage']:
                node.archive_job.update_target(addon, ARCHIVER_INITIATED)
        for addon in ['dropbox', 'osfstorage']:
            rchild.archive_job.update_target(addon, ARCHIVER_SUCCESS)
        rchild.save()
        listeners.archive_callback(rchild)
        mock_send_success.assert_not_called()
        for addon in ['dropbox', 'osfstorage']:
            reg.archive_job.update_target(addon, ARCHIVER_SUCCESS)
        reg.save()
        listeners.archive_callback(reg)
        mock_send_success.assert_not_called()
        for addon in ['dropbox', 'osfstorage']:
            rchild2.archive_job.update_target(addon, ARCHIVER_SUCCESS)
        rchild2.save()
        listeners.archive_callback(rchild2)
        mock_send_success.assert_called()

class TestArchiverScripts(ArchiverTestCase):

    def test_find_failed_registrations(self):
        failures = []
        legacy = []
        delta = datetime.timedelta(days=2)
        for i in range(5):
            reg = factories.RegistrationFactory()
            reg.archive_job._fields['datetime_initiated'].__set__(
                reg.archive_job,
                datetime.datetime.now() - delta,
                safe=True
            )
            reg.save()
            ArchiveJob.remove_one(reg.archive_job)
            legacy.append(reg._id)
        for i in range(5):
            reg = factories.RegistrationFactory()
            reg.archive_job._fields['datetime_initiated'].__set__(
                reg.archive_job,
                datetime.datetime.now() - delta,
                safe=True
            )
            reg.archive_job.status = ARCHIVER_INITIATED
            reg.archive_job.save()
            reg.save()
            for addon in ['osfstorage', 'dropbox']:
                reg.archive_job._set_target(addon)
                reg.archive_job.update_target(addon, ARCHIVER_INITIATED)
            reg.archive_job.sent = False
            reg.archive_job.save()
            failures.append(reg._id)
        pending = []
        for i in range(5):
            reg = factories.RegistrationFactory()
            for addon in ['osfstorage', 'dropbox']:
                reg.archive_job._set_target(addon)
                reg.archive_job.update_target(addon, ARCHIVER_INITIATED)
            reg.archive_job.save()
            pending.append(reg)
        failed = scripts.find_failed_registrations()
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

    @mock.patch('website.project.model.Node.update_search')
    def test_archiving_registrations_not_added_to_search_before_archival(self, mock_update_search):
        proj = factories.ProjectFactory()
        reg = factories.RegistrationFactory(project=proj)
        reg.save()
        mock_update_search.assert_not_called()


    @mock.patch('website.project.model.Node.update_search')
    @mock.patch('website.mails.send_mail')
    @mock.patch('website.archiver.tasks.archive_success.delay')
    def test_archiving_nodes_added_to_search_on_archive_success_if_public(self, mock_send, mock_update_search, mock_archive_success):
        proj = factories.ProjectFactory()
        reg = factories.RegistrationFactory(project=proj)
        reg.save()
        with nested(
                mock.patch('website.archiver.model.ArchiveJob.archive_tree_finished', mock.Mock(return_value=True)),
                mock.patch('website.archiver.model.ArchiveJob.sent', mock.PropertyMock(return_value=False)),
                mock.patch('website.archiver.model.ArchiveJob.success', mock.PropertyMock(return_value=True))
        ) as (mock_finished, mock_sent, mock_success):
            listeners.archive_callback(reg)
        mock_update_search.assert_called_once()

    @mock.patch('website.project.model.Node.update_search')
    @mock.patch('website.mails.send_mail')
    def test_archiving_nodes_not_added_to_search_on_archive_failure(self, mock_send, mock_update_search):
        proj = factories.ProjectFactory()
        reg = factories.RegistrationFactory(project=proj)
        reg.save()
        with nested(
                mock.patch('website.archiver.model.ArchiveJob.archive_tree_finished', mock.Mock(return_value=True)),
                mock.patch('website.archiver.model.ArchiveJob.sent', mock.PropertyMock(return_value=False)),
                mock.patch('website.archiver.model.ArchiveJob.success', mock.PropertyMock(return_value=False))
        ) as (mock_finished, mock_sent, mock_success):
            listeners.archive_callback(reg)
        mock_update_search.assert_not_called()

    @mock.patch('website.project.model.Node.update_search')
    @mock.patch('website.mails.send_mail')
    def test_archiving_nodes_not_added_to_search_on_archive_incomplete(self, mock_send, mock_update_search):
        proj = factories.ProjectFactory()
        reg = factories.RegistrationFactory(project=proj)
        reg.save()
        with mock.patch('website.archiver.model.ArchiveJob.archive_tree_finished', mock.Mock(return_value=False)):
            listeners.archive_callback(reg)
        mock_update_search.assert_not_called()


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
        job = ArchiveJob()
        job.target_addons.append(target)

        result = job.target_info()
        assert_equal(len(result), 1)

        item = result[0]

        assert_equal(item['name'], target.name)
        assert_equal(item['status'], target.status)
        assert_equal(item['stat_result'], target.stat_result)
        assert_equal(item['errors'], target.errors)

    @use_fake_addons
    def test_get_target(self):
        proj = factories.ProjectFactory()
        reg = factories.RegistrationFactory(project=proj)
        job = ArchiveJob(src_node=proj, dst_node=reg, initiator=proj.creator)
        job.set_targets()
        dropbox = job.get_target('dropbox')
        assert_false(not dropbox)
        none = job.get_target('fake')
        assert_false(none)

    @use_fake_addons
    def test_set_targets(self):
        proj = factories.ProjectFactory()
        reg = factories.RegistrationFactory(project=proj)
        job = ArchiveJob(src_node=proj, dst_node=reg, initiator=proj.creator)
        job.set_targets()
        assert_equal([t.name for t in job.target_addons], ['osfstorage', 'dropbox'])

    def test_archive_tree_finished(self):
        proj = factories.NodeFactory()
        factories.NodeFactory(parent=proj)
        comp2 = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=comp2)
        reg = factories.RegistrationFactory(project=proj)
        rchild1 = reg.nodes[0]
        rchild2 = reg.nodes[1]
        rchild2a = rchild2.nodes[0]
        regs = itertools.chain([reg], reg.get_descendants_recursive())
        for node in regs:
            assert_false(node.archive_job.archive_tree_finished())
        for node in regs:
            assert_false(node.archive_job.archive_tree_finished())
        for node in [reg, rchild2]:
            for target in node.archive_job.target_addons:
                node.archive_job.update_target(target.name, ARCHIVER_SUCCESS)
        for node in regs:
            assert_true(node.archive_job.archive_tree_finished())
