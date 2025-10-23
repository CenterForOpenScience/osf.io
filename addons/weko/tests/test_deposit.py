# -*- coding: utf-8 -*-
import logging
import mock
from nose.tools import *  # noqa
import json
import os
import tempfile
from zipfile import ZipFile

from framework.auth import Auth
from osf.models.metaschema import RegistrationSchema
from osf_tests.factories import UserFactory, NodeFactory
from tests.base import OsfTestCase

from addons.weko import deposit


logger = logging.getLogger(__name__)


class TestWEKOBagIt(OsfTestCase):

    def setUp(self):
        super(TestWEKOBagIt, self).setUp()
        self.user = UserFactory()
        self.node = NodeFactory(creator=self.user)
        self.node.add_addon('weko', auth=Auth(self.user))

    def tearDown(self):
        super(TestWEKOBagIt, self).tearDown()

    @mock.patch('addons.weko.deposit.WaterButlerClient')
    @mock.patch('addons.weko.models.NodeSettings.create_client')
    @mock.patch('addons.weko.models.NodeSettings.create_waterbutler_deposit_log')
    def test_single_file(self, mock_create_log, mock_create_client, mock_wb):
        index_id = 'test_index_id'
        target_schema = RegistrationSchema.objects \
            .filter(name='公的資金による研究データのメタデータ登録') \
            .order_by('-schema_version') \
            .first()
        file_metadata = {
            'items': [
                {
                    'schema': target_schema._id,
                    'data': {
                        'grdm-file:title-en': {
                            'value': 'ENGLISH TITLE',
                        },
                        'grdm-file:data-description-ja': {
                            'value': '日本語説明',
                        },
                    },
                },
            ],
        }
        project_metadata = {
            'funder': {
                'value': 'JST',
            },
            'funding-stream-code': {
                'value': 'JPTEST',
            },
            'program-name-ja': {
                'value': 'テストプログラム',
            },
            'program-name-en': {
                'value': 'Test Program',
            },
            'japan-grant-number': {
                'value': 'JP123456',
            },
            'project-name-ja': {
                'value': 'テストプロジェクト',
            },
            'project-name-en': {
                'value': 'Test Project',
            },
        }

        mock_wb_instance = mock.MagicMock()
        mock_wb.return_value = mock_wb_instance
        mock_wb_client = mock.MagicMock()
        mock_wb_instance.get_client_for_node.return_value = mock_wb_client
        dummy_text = 'This is a dummy text.'
        mock_file = mock.MagicMock(
            kind='file', size=len(dummy_text), name='dummy',
        )
        mock_file.name = 'dummy'
        def write_dummy_file(f):
            f.write(dummy_text.encode('utf-8'))
        mock_file.download_to.side_effect = write_dummy_file
        mock_wb_client.get_file_by_materialized_path.return_value = mock_file

        mock_client = mock.MagicMock()
        mock_create_client.return_value = mock_client

        deposit._deposit_metadata(
            self.user._id, index_id, self.node._id, '',
            target_schema._id, [file_metadata], [project_metadata],
            ['/path/to/dummy'], '/path/to/status',
        )

        # check headers
        mock_client.deposit.assert_called_once()
        deposit_kwargs = mock_client.deposit.call_args[1]
        assert_equal(deposit_kwargs['headers']['Packaging'], 'http://purl.org/net/sword/3.0/package/SimpleZip')
        assert_equal(deposit_kwargs['headers']['Content-Disposition'], 'attachment; filename=payload.zip')

        # check files
        files = mock_client.deposit.call_args[0]
        filename, content_reader, mimetype = files[0]['file']
        assert_equal(filename, 'payload.zip')
        assert_equal(mimetype, 'application/zip')
        logger.info(f'Reader: {content_reader}')

        # unzip the files of content_reader
        tmp_dir = tempfile.mkdtemp()
        with ZipFile(content_reader, 'r') as zipf:
            zipf.extractall(tmp_dir)
        assert_true(os.path.exists(os.path.join(tmp_dir, 'bagit.txt')))
        assert_true(os.path.exists(os.path.join(tmp_dir, 'bag-info.txt')))
        assert_true(os.path.exists(os.path.join(tmp_dir, 'tagmanifest-sha256.txt')))
        assert_true(os.path.exists(os.path.join(tmp_dir, 'manifest-sha256.txt')))
        assert_true(os.path.exists(os.path.join(tmp_dir, 'manifest-sha512.txt')))
        assert_true(os.path.exists(os.path.join(tmp_dir, 'data/index.csv')))
        assert_true(os.path.exists(os.path.join(tmp_dir, 'data/ro-crate-metadata.json')))
        assert_true(os.path.exists(os.path.join(tmp_dir, 'data/files/dummy')))

        assert_equal(open(os.path.join(tmp_dir, 'data/files/dummy'), 'r').read(), dummy_text)
        bagit_content = open(os.path.join(tmp_dir, 'bagit.txt'), 'r').read()
        logger.info(f'BagIt: {bagit_content}')
        assert_in('Tag-File-Character-Encoding: UTF-8', bagit_content)
        bag_info_content = open(os.path.join(tmp_dir, 'bag-info.txt'), 'r').read()
        logger.info(f'BagInfo: {bag_info_content}')
        assert_in('Contact-Name: ', bag_info_content)
        tagmanifest_sha256_content = open(os.path.join(tmp_dir, 'tagmanifest-sha256.txt'), 'r').read()
        logger.info(f'TagManifest: {tagmanifest_sha256_content}')
        assert_not_in('data/index.csv', tagmanifest_sha256_content)
        manifest_sha256_content = open(os.path.join(tmp_dir, 'manifest-sha256.txt'), 'r').read()
        logger.info(f'Manifest: {manifest_sha256_content}')
        assert_in('data/index.csv', manifest_sha256_content)
        assert_in('data/ro-crate-metadata.json', manifest_sha256_content)
        assert_in('data/files/dummy', manifest_sha256_content)
        manifest_sha512_content = open(os.path.join(tmp_dir, 'manifest-sha512.txt'), 'r').read()
        logger.info(f'Manifest: {manifest_sha512_content}')
        assert_in('data/index.csv', manifest_sha512_content)
        assert_in('data/ro-crate-metadata.json', manifest_sha512_content)
        assert_in('data/files/dummy', manifest_sha512_content)
        index_csv_content = open(os.path.join(tmp_dir, 'data/index.csv'), 'r').read()
        logger.info(f'Index CSV: {index_csv_content}')
        assert_in('ENGLISH TITLE', index_csv_content)
        assert_in('日本語説明', index_csv_content)
        ro_crate_metadata_content = open(os.path.join(tmp_dir, 'data/ro-crate-metadata.json'), 'r').read()
        logger.info(f'RO-Crate Metadata: {ro_crate_metadata_content}')
        assert_in('@graph', json.loads(ro_crate_metadata_content))
        assert_in('ENGLISH TITLE', ro_crate_metadata_content)
        assert_in('日本語説明', ro_crate_metadata_content)

        mock_create_log.assert_called_once()
