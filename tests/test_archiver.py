import json
import celery
from faker import Faker
import datetime
from modularodm import Q
import requests

import mock  # noqa
from mock import call
from nose.tools import *  # noqa PEP8 asserts
import httpretty

from scripts import cleanup_failed_registrations as scripts

from framework.auth import Auth
from framework.tasks import handlers

from website.archiver import (
    ARCHIVER_CHECKING,
    ARCHIVER_PENDING,
    ARCHIVER_SUCCESS,
    ARCHIVER_FAILURE,
    ARCHIVER_NETWORK_ERROR,
    ARCHIVER_SIZE_EXCEEDED,
)
from website.archiver import utils as archiver_utils
from website.app import *  # noqa
from website import archiver
from website.archiver import listeners
from website.archiver.tasks import *   # noqa

from website import mails
from website import settings
from website.util import waterbutler_url_for
from website.project.model import Node
from website.addons.base import StorageAddonBase
from website.util import api_url_for

from tests import factories
from tests.base import OsfTestCase

fake = Faker()

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

class ArchiverTestCase(OsfTestCase):
    def setUp(self):
        super(ArchiverTestCase, self).setUp()
        handlers.celery_before_request()
        self.user = factories.UserFactory()
        self.auth = Auth(user=self.user)
        self.src = factories.NodeFactory(creator=self.user)
        self.src.add_addon('dropbox', auth=self.auth)
        self.dst = factories.RegistrationFactory(user=self.user, project=self.src, send_signals=False)
        self.stat_result = archiver_utils.aggregate_file_tree_metadata('dropbox', FILE_TREE, self.user)
        self.pks = (self.src._id, self.dst._id, self.user._id)

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
        #  Test that each addon in settings.ADDONS_ARCHIVABLE if addon not in ['osfstorage', 'wiki'] implements the StorageAddonBase interface
        for addon in [a for a in settings.ADDONS_ARCHIVABLE if a not in ['osfstorage', 'wiki']]:
            self._test_addon(addon)

class TestArchiverTasks(ArchiverTestCase):

    @mock.patch('celery.chord')
    @mock.patch('website.archiver.tasks.stat_addon.si')
    @mock.patch('website.archiver.tasks.archive_node.s')
    def test_archive(self, mock_archive, mock_stat, mock_chord):
        src_pk, dst_pk, user_pk = self.pks
        archive(src_pk, dst_pk, user_pk)
        targets = [self.src.get_addon(name) for name in settings.ADDONS_ARCHIVABLE]
        chain_sig = celery.group(
            stat_addon.si(
                addon_short_name=addon.config.short_name,
                src_pk=src_pk,
                dst_pk=dst_pk,
                user_pk=user_pk,
            )
            for addon in targets if (addon and addon.complete and isinstance(addon, StorageAddonBase))
        )
        assert_true(self.dst.archiving)
        mock_chord.assert_called_with(chain_sig)

    def test_stat_addon(self):
        src_pk, dst_pk, user_pk = self.pks
        with mock.patch.object(StorageAddonBase, '_get_file_tree') as mock_file_tree:
            with mock.patch.object(archiver, 'AggregateStatResult') as MockStat:
                mock_file_tree.return_value = FILE_TREE
                res = stat_addon('dropbox', src_pk,  dst_pk, user_pk)
        assert_equal(self.dst.archived_providers['dropbox']['status'], ARCHIVER_CHECKING)
        src_dropbox = self.src.get_addon('dropbox')
        assert(MockStat.called_with(
            src_dropbox._id,
            'dropbox',
            targets=[archiver_utils.aggregate_file_tree_metadata(src_dropbox, FILE_TREE, self.user)]
        ))
        assert_equal(res.target_name, 'dropbox')

    @mock.patch('website.archiver.tasks.archive_addon.delay')
    def test_archive_node_pass(self, mock_archive_addon):
        settings.MAX_ARCHIVE_SIZE = 1024 ** 3
        src_pk, dst_pk, user_pk = self.pks
        with mock.patch.object(StorageAddonBase, '_get_file_tree') as mock_file_tree:
            mock_file_tree.return_value = FILE_TREE
            results = [stat_addon(addon, src_pk, dst_pk, user_pk) for addon in ['osfstorage', 'dropbox']]
        with mock.patch.object(celery, 'group') as mock_group:
            archive_node(results, src_pk, dst_pk, user_pk)
        archive_dropbox_signature = archive_addon.si(
            'dropbox',
            src_pk,
            dst_pk,
            user_pk,
            results
        )
        assert(mock_group.called_with(archive_dropbox_signature))

    def test_archive_node_fail(self):
        settings.MAX_ARCHIVE_SIZE = 100
        src_pk, dst_pk, user_pk = self.pks
        with mock.patch.object(StorageAddonBase, '_get_file_tree') as mock_file_tree:
            mock_file_tree.return_value = FILE_TREE
            results = [stat_addon(addon, src_pk, dst_pk, user_pk) for addon in ['osfstorage', 'dropbox']]
        with mock.patch('website.archiver.tasks.ArchiverTask.on_failure') as mock_fail:
            try:
                archive_node.apply(args=(results, src_pk, dst_pk, user_pk))
            except:
                pass
        assert_true(isinstance(mock_fail.call_args[0][0], ArchiverSizeExceeded))

    @mock.patch('website.archiver.tasks.archive_addon.delay')
    def test_archive_node_does_not_archive_empty_addons(self, mock_archive_addon):
        src_pk, dst_pk, user_pk = self.pks
        with mock.patch.object(StorageAddonBase, '_get_file_tree') as mock_file_tree:
            mock_file_tree.return_value = {
                'path': '/',
                'kind': 'folder',
                'name': 'Fake',
                'children': []
            }
            results = [stat_addon(addon, src_pk, dst_pk, user_pk) for addon in ['osfstorage', 'dropbox']]
            archive_node(results, src_pk=src_pk, dst_pk=dst_pk, user_pk=user_pk)
        mock_archive_addon.assert_not_called()

    @mock.patch('website.archiver.tasks.make_copy_request.delay')
    def test_archive_addon(self, mock_make_copy_request):
        src_pk, dst_pk, user_pk = self.pks
        result = archiver_utils.aggregate_file_tree_metadata('dropbox', FILE_TREE, self.user),
        archive_addon('dropbox', src_pk, dst_pk, user_pk, result)
        assert_equal(self.dst.archived_providers['dropbox']['status'], ARCHIVER_PENDING)
        cookie = self.user.get_or_create_cookie()
        assert(mock_make_copy_request.called_with(
            src_pk,
            dst_pk,
            user_pk,
            settings.WATERBUTLER_URL + '/ops/copy',
            data=dict(
                source=dict(
                    cookie=cookie,
                    nid=src_pk,
                    provider='dropbox',
                    path='/',
                ),
                destination=dict(
                    cookie=cookie,
                    nid=dst_pk,
                    provider=settings.ARCHIVE_PROVIDER,
                    path='/',
                ),
                rename='Archive of DropBox',
            )
        ))

    @httpretty.activate
    def test_make_copy_request_20X(self):
        src_pk, dst_pk, user_pk = self.pks
        def callback_OK(request, uri, headers):
            return (200, headers, json.dumps({}))

        self.dst.archived_providers = {
            'dropbox': {
                'status': ARCHIVER_PENDING
            }
        }
        self.dst.save()
        url = 'http://' + fake.ipv4()
        httpretty.register_uri(httpretty.POST,
                               url,
                               body=callback_OK,
                               content_type='application/json')
        with mock.patch.object(project_signals, 'archive_callback') as mock_callback:
            make_copy_request(src_pk, dst_pk, user_pk,
                              url, {
                                  'source': {
                                      'provider': 'dropbox'
                                  }
                              })
        assert_equal(self.dst.archived_providers['dropbox']['status'], ARCHIVER_SUCCESS)
        assert(mock_callback.called_with(self.dst))

    @httpretty.activate
    def test_make_copy_request_error(self):
        error = {'errors': ['BAD REQUEST']}
        src_pk, dst_pk, user_pk = self.pks
        def callback_400(request, uri, headers):
            return (400, headers, json.dumps(error))

        self.dst.archived_providers = {
            'dropbox': {
                'status': ARCHIVER_PENDING
            }
        }
        self.dst.save()

        url = 'http://' + fake.ipv4()
        httpretty.register_uri(httpretty.POST,
                               url,
                               body=callback_400,
                               content_type='application/json')
        with mock.patch('website.archiver.utils.update_status') as mock_update:
            try:
                make_copy_request(src_pk, dst_pk, user_pk,
                                  url, {
                                      'source': {
                                          'provider': 'dropbox'
                                      }
                                  })
            except HTTPError:
                pass
        mock_update.assert_called_with(self.dst, 'dropbox', ARCHIVER_FAILURE, meta={'errors': [error]})

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
            stat_result={},
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

    def test_update_status(self):
        self.dst.archived_providers['test'] = {
            'status': 'OK',
        }
        self.dst.save()
        archiver_utils.update_status(self.dst, 'test', 'BAD', meta={'meta': 'DATA'})
        assert_equal(self.dst.archived_providers['test']['status'], 'BAD')
        assert_equal(self.dst.archived_providers['test']['meta'], 'DATA')

    def test_aggregate_file_tree_metadata(self):
        a_stat_result = archiver_utils.aggregate_file_tree_metadata('dropbox', FILE_TREE, self.user)
        assert_equal(a_stat_result.disk_usage, 128 + 256)
        assert_equal(a_stat_result.num_files, 2)
        assert_equal(len(a_stat_result.targets), 2)

    def test_archive_provider_for(self):
        provider = self.src.get_addon(settings.ARCHIVE_PROVIDER)
        assert_equal(archiver_utils.archive_provider_for(self.src, self.user)._id, provider._id)

    def test_has_archive_provider(self):
        assert_true(archiver_utils.has_archive_provider(self.src, self.user))
        wo = factories.NodeFactory(user=self.user)
        wo.delete_addon(settings.ARCHIVE_PROVIDER, auth=self.auth, _force=True)
        assert_false(archiver_utils.has_archive_provider(wo, self.user))

    def test_link_archive_provider(self):
        wo = factories.NodeFactory(user=self.user)
        wo.delete_addon(settings.ARCHIVE_PROVIDER, auth=self.auth, _force=True)
        archiver_utils.link_archive_provider(wo, self.user)
        assert_true(archiver_utils.has_archive_provider(wo, self.user))

    def test_delete_registration_tree(self):
        proj = factories.NodeFactory()
        factories.NodeFactory(parent=proj)
        comp2 = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=comp2)
        reg = factories.RegistrationFactory(project=proj)
        reg_ids = [reg._id] + [r._id for r in reg.get_descendants_recursive()]
        archiver_utils.delete_registration_tree(reg)
        assert_false(Node.find(Q('_id', 'in', reg_ids) & Q('is_deleted', 'eq', False)).count())

    def test_delete_registration_tree_deletes_backrefs(self):
        proj = factories.NodeFactory()
        factories.NodeFactory(parent=proj)
        comp2 = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=comp2)
        reg = factories.RegistrationFactory(project=proj)
        archiver_utils.delete_registration_tree(reg)
        assert_false(proj.node__registrations)

class TestArchiverListeners(ArchiverTestCase):

    def test_after_register(self):
        with mock.patch.object(handlers, 'enqueue_task') as mock_queue:
            listeners.after_register(self.src, self.dst, self.user)
        archive_signature = archive.si(self.src._id, self.dst._id, self.user._id)
        assert(mock_queue.called_with(archive_signature))

    def test_archive_callback_pending(self):
        self.dst.archived_providers = {
            addon: {
                'status': ARCHIVER_PENDING
            } for addon in settings.ADDONS_ARCHIVABLE if addon not in ['osfstorage', 'wiki']
        }
        self.dst.archived_providers['osfstorage'] = {
            'status': ARCHIVER_SUCCESS
        }
        self.dst.save()
        with mock.patch('website.archiver.utils.send_archiver_success_mail') as mock_send:
            with mock.patch('website.archiver.utils.handle_archive_fail') as mock_fail:
                listeners.archive_callback(self.dst)
        assert_false(mock_send.called)
        assert_false(mock_fail.called)

    @mock.patch('website.archiver.utils.send_archiver_success_mail')
    def test_archive_callback_done_success(self, mock_send):
        self.dst.archiving = True
        for addon in self.dst.archived_providers:
            self.dst.archived_providers[addon]['status'] = ARCHIVER_SUCCESS
        self.dst.save()
        listeners.archive_callback(self.dst)
        mock_send.assert_called_with(self.dst)

    @mock.patch('website.project.utils.send_embargo_email')
    def test_archive_callback_done_embargoed(self, mock_send):
        self.dst.archiving = True
        end_date = datetime.datetime.now() + datetime.timedelta(days=30)
        self.dst.embargo_registration(self.user, end_date)
        for addon in self.dst.archived_providers:
            self.dst.archived_providers[addon]['status'] = ARCHIVER_SUCCESS
        self.dst.save()
        listeners.archive_callback(self.dst)
        mock_send.assert_called_with(self.dst, self.user)

    def test_archive_callback_done_errors(self):
        self.dst.archived_providers = {
            addon: {
                'status': ARCHIVER_SUCCESS
            } for addon in settings.ADDONS_ARCHIVABLE if addon not in ['osfstorage', 'wiki']
        }
        self.dst.archived_providers['box']['status'] = ARCHIVER_FAILURE
        self.dst.save()
        with mock.patch('website.archiver.utils.handle_archive_fail') as mock_fail:
            listeners.archive_callback(self.dst)
        assert(mock_fail.called_with(ARCHIVER_NETWORK_ERROR, self.src, self.dst, self.user, self.dst.archived_providers))

    def test_archive_callback_updates_achiving_state_when_done(self):
        proj = factories.NodeFactory()
        factories.NodeFactory(parent=proj)
        reg = factories.RegistrationFactory(project=proj)
        reg.archiving = True
        reg.archived_providers = {
            addon: {
                'status': ARCHIVER_PENDING,
            }
            for addon in ['box', 'osfstorage']
        }
        child = reg.nodes[0]
        child.archiving = True
        child.archived_providers = {
            addon: {
                'status': ARCHIVER_SUCCESS,
            }
            for addon in ['box', 'osfstorage']
        }
        child.save()
        listeners.archive_callback(child)
        assert_false(child.archiving)

    def test_archive_tree_finished_d1(self):
        self.dst.archived_providers = {
            addon: {
                'status': ARCHIVER_SUCCESS
            }
            for addon in ['box', 'osfstorage']
        }
        self.dst.save()
        assert_true(listeners.archive_tree_finished)

    def test_archive_tree_finished_d3(self):
        proj = factories.NodeFactory()
        child = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=child)
        reg = factories.RegistrationFactory(project=proj)
        rchild = reg.nodes[0]
        rchild2 = rchild.nodes[0]
        for node in [reg, rchild, rchild2]:
            node.archived_providers = {
                addon: {
                    'status': ARCHIVER_SUCCESS
                }
                for addon in ['box', 'osfstorage']
            }
            node.save()
            node.reload()
        for node in [reg, rchild, rchild2]:
            assert_true(listeners.archive_tree_finished(node))

    def test_archive_tree_finished_false(self):
        proj = factories.NodeFactory()
        child = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=child)
        reg = factories.RegistrationFactory(project=proj)
        rchild = reg.nodes[0]
        rchild2 = rchild.nodes[0]
        for node in [reg, rchild, rchild2]:
            node.archived_providers = {
                addon: {
                    'status': ARCHIVER_SUCCESS
                }
                for addon in ['box', 'osfstorage']
            }
            node.save()
            node.reload()
        rchild.archived_providers.update({
            'box': {
                'status': ARCHIVER_CHECKING,
            },
        })
        rchild.save()
        rchild.reload()
        for node in [reg, rchild, rchild2]:
            assert_false(listeners.archive_tree_finished(node))

    @mock.patch('website.archiver.utils.send_archiver_success_mail')
    def test_archive_callback_on_tree_sends_only_one_email(self, mock_send_success):
        proj = factories.NodeFactory()
        child = factories.NodeFactory(parent=proj)
        factories.NodeFactory(parent=child)
        reg = factories.RegistrationFactory(project=proj)
        rchild = reg.nodes[0]
        rchild2 = rchild.nodes[0]
        for node in [reg, rchild, rchild2]:
            node.archiving = True
            node.save()
        rchild.archived_providers = {
            addon: {
                'status': ARCHIVER_SUCCESS
            }
            for addon in ['box', 'osfstorage']
        }
        rchild.save()
        listeners.archive_callback(rchild)
        mock_send_success.assert_not_called()
        reg.archived_providers = {
            addon: {
                'status': ARCHIVER_SUCCESS
            }
            for addon in ['box', 'osfstorage']
        }
        reg.save()
        listeners.archive_callback(reg)
        mock_send_success.assert_not_called()
        rchild2.archived_providers = {
            addon: {
                'status': ARCHIVER_SUCCESS
            }
            for addon in ['box', 'osfstorage']
        }
        rchild2.save()
        listeners.archive_callback(rchild2)
        mock_send_success.assert_called_with(rchild2)

class TestArchiverScripts(ArchiverTestCase):

    def test_find_failed_registrations(self):
        failures = []
        delta = datetime.timedelta(2)
        for i in range(5):
            reg = factories.RegistrationFactory()
            reg._fields['registered_date'].__set__(
                reg,
                datetime.datetime.now() - delta,
                safe=True
            )
            reg.archived_providers = {
                addon: {
                    'status': ARCHIVER_PENDING
                } for addon in settings.ADDONS_ARCHIVABLE if not addon == 'wiki'
            }
            reg.archiving = True
            reg.save()
            failures.append(reg)
        pending = []
        for i in range(5):
            reg = factories.RegistrationFactory()
            reg.archived_providers = {
                addon: {
                    'status': ARCHIVER_PENDING
                } for addon in settings.ADDONS_ARCHIVABLE if not addon == 'wiki'
            }
            reg.archiving = True
            reg.save()
            pending.append(reg)
        failed = scripts.find_failed_registrations()
        assert_equal(failed.get_keys(), [f._id for f in failures])

class TestArchiverDebugRoutes(ArchiverTestCase):

    def test_debug_route_does_not_exist(self):
        route = None
        try:
            route = api_url_for('archiver_debug', nid=self.dst._id)
            assert(False)
        except AssertionError:
            assert(False)
        except:
            assert(True)
        if route:
            try:
                self.app.get(route)
                assert(False)
            except AssertionError:
                assert(False)
            except:
                assert(True)
