# -*- coding: utf-8 -*-
import csv
import io
import json
import logging
import mock
from mock import call
from nose.tools import *  # noqa
import re

from osf.models.metaschema import RegistrationSchema
from osf_tests.factories import UserFactory
from tests.base import OsfTestCase

from addons.weko import schema


logger = logging.getLogger(__name__)


def _transpose(lines):
    assert len(set([len(l) for l in lines])) == 1, set([len(l) for l in lines])
    return [[row[i] for row in lines] for i in range(len(lines[0]))]


class TestWEKOSchema(OsfTestCase):

    def setUp(self):
        super(TestWEKOSchema, self).setUp()
        self.user = UserFactory()

    def tearDown(self):
        super(TestWEKOSchema, self).tearDown()

    def test_write_csv_minimal(self):
        buf = io.StringIO()
        index = mock.MagicMock()
        index.identifier = '1000'
        index.title = 'TITLE'
        files = [
            ('test.jpg', 'image/jpeg'),
        ]
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

        schema.write_csv(
            self.user,
            buf,
            index,
            files,
            target_schema._id,
            [file_metadata],
            [],
        )

        logger.info(f'CSV: {buf.getvalue()}')
        buf.seek(0)
        reader = csv.reader(buf)
        lines = list(reader)
        assert_equal(len(lines), 6)
        assert_equal(lines[0], [
            '#ItemType',
            'デフォルトアイテムタイプ（フル）(30002)',
            'https://localhost:8443/items/jsonschema/30002',
        ])
        props = _transpose(lines[1::])[::-1]

        assert_equal(
            props.pop(),
            ['.publish_status', '.PUBLISH_STATUS', '', 'Required', 'private'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.path[0]', '.IndexID[0]', '', 'Allow Multiple', '1000'],
        )
        assert_equal(
            props.pop(),
            ['.pos_index[0]', '.POS_INDEX[0]', '', 'Allow Multiple', 'TITLE'],
        )
        assert_equal(
            props.pop(),
            ['.file_path[0]', '.ファイルパス[0]', '', 'Allow Multiple', 'test.jpg'],
        )
        feedback_mail = props.pop()
        assert_equal(
            feedback_mail[:-1],
            ['.feedback_mail[0]', '', '', ''],
        )
        assert_true(
            re.match(r'[^@]+@[^@]+\.[^@]+', feedback_mail[-1])
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_file35[0].accessrole', '', '', '', 'open_no'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_file35[0].displaytype', '', '', '', 'preview'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_file35[0].filename', '', '', '', 'test.jpg'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_file35[0].format', '', '', '', 'image/jpeg'],
        )
        pub_date = props.pop()
        assert_equal(
            pub_date[:-1],
            ['.metadata.pubdate', '', '', ''],
        )
        assert_true(
            re.match(r'[0-9]+\-[0-9]+\-[0-9]+', pub_date[-1])
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_description9[0].subitem_description', '', '', '', '日本語説明'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_description9[0].subitem_description_language', '', '', '', 'ja'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_description9[0].subitem_description_type', '', '', '', 'Abstract'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_resource_type13.resourcetype', '', '', '', 'dataset'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_title0[0].subitem_title', '', '', '', 'ENGLISH TITLE'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_title0[0].subitem_title_language', '', '', '', 'en'],
        )
        assert_equal(
            props.pop(),
            ['#.id', '#ID', '#', '#', ''],
        )
        assert_equal(
            props.pop(),
            ['.uri', 'URI', '', '', ''],
        )
        assert_equal(
            props.pop(),
            ['.cnri', '.CNRI', '', '', ''],
        )
        assert_equal(
            props.pop(),
            ['.doi_ra', '.DOI_RA', '', '', ''],
        )
        assert_equal(
            props.pop(),
            ['.doi', '.DOI', '', '', ''],
        )
        assert_equal(
            props.pop(),
            ['.edit_mode', 'Keep/Upgrade Version', '', 'Required', 'Keep'],
        )

    def test_write_csv_full(self):
        buf = io.StringIO()
        index = mock.MagicMock()
        index.identifier = '1000'
        index.title = 'TITLE'
        files = [
            ('test.jpg', 'image/jpeg'),
        ]
        target_schema = RegistrationSchema.objects \
            .filter(name='公的資金による研究データのメタデータ登録') \
            .order_by('-schema_version') \
            .first()
        file_metadata = {
            'items': [
                {
                    'schema': target_schema._id,
                    'data': dict([(k, {
                        'value': v,
                    })for k, v in {
                        'grdm-file:data-number': '00001',
                        'grdm-file:title-en': 'TEST DATA',
                        'grdm-file:title-ja': 'テストデータ',
                        'grdm-file:date-issued-updated': '2023-09-15',
                        'grdm-file:data-description-ja': 'テスト説明',
                        'grdm-file:data-description-en': 'TEST DESCRIPTION',
                        'grdm-file:data-research-field': '189',
                        'grdm-file:data-type': 'experimental data',
                        'grdm-file:file-size': '29.9KB',
                        'grdm-file:data-policy-free': 'free',
                        'grdm-file:data-policy-license': 'CC0',
                        'grdm-file:data-policy-cite-ja': 'ライセンスのテスト',
                        'grdm-file:data-policy-cite-en': 'Test for license',
                        'grdm-file:access-rights': 'restricted access',
                        'grdm-file:available-date': '',
                        'grdm-file:repo-information-ja': 'テストリポジトリ',
                        'grdm-file:repo-information-en': 'Test Repository',
                        'grdm-file:repo-url-doi-link': 'http://localhost:5000/q3gnm/files/osfstorage/650e68f8c00e45055fc9e0ac',
                        'grdm-file:creators': [
                            {
                                'number': '22222',
                                'name-ja': '情報太郎',
                                'name-en': 'Taro Joho',
                            }
                        ],
                        'grdm-file:hosting-inst-ja': '国立情報学研究所',
                        'grdm-file:hosting-inst-en': 'National Institute of Informatics',
                        'grdm-file:hosting-inst-id': 'https://ror.org/04ksd4g47',
                        'grdm-file:data-man-type': 'individual',
                        'grdm-file:data-man-number': '11111',
                        'grdm-file:data-man-name-ja': '情報花子',
                        'grdm-file:data-man-name-en': 'Hanako Joho',
                        'grdm-file:data-man-org-ja': '国立情報学研究所',
                        'grdm-file:data-man-org-en': 'National Institute of Informatics',
                        'grdm-file:data-man-address-ja': '一ツ橋',
                        'grdm-file:data-man-address-en': 'Hitotsubashi',
                        'grdm-file:data-man-tel': 'XX-XXXX-XXXX',
                        'grdm-file:data-man-email': 'dummy@test.rcos.nii.ac.jp',
                        'grdm-file:remarks-ja': 'コメント',
                        'grdm-file:remarks-en': 'Comment',
                        'grdm-file:metadata-access-rights': 'closed access',
                    }.items()]),
                },
            ],
        }

        schema.write_csv(
            self.user,
            buf,
            index,
            files,
            target_schema._id,
            [file_metadata],
            [],
        )

        logger.info(f'CSV: {buf.getvalue()}')
        buf.seek(0)
        reader = csv.reader(buf)
        lines = list(reader)
        assert_equal(len(lines), 6)
        logger.info(repr(lines))
        assert_equal(lines[0], [
            '#ItemType',
            'デフォルトアイテムタイプ（フル）(30002)',
            'https://localhost:8443/items/jsonschema/30002',
        ])
        props = _transpose(lines[1::])[::-1]

        assert_equal(
            props.pop(),
            ['.publish_status', '.PUBLISH_STATUS', '', 'Required', 'private'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.path[0]', '.IndexID[0]', '', 'Allow Multiple', '1000'],
        )
        assert_equal(
            props.pop(),
            ['.pos_index[0]', '.POS_INDEX[0]', '', 'Allow Multiple', 'TITLE'],
        )
        assert_equal(
            props.pop(),
            ['.file_path[0]', '.ファイルパス[0]', '', 'Allow Multiple', 'test.jpg'],
        )
        feedback_mail = props.pop()
        assert_equal(
            feedback_mail[:-1],
            ['.feedback_mail[0]', '', '', ''],
        )
        assert_true(
            re.match(r'[^@]+@[^@]+\.[^@]+', feedback_mail[-1])
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_file35[0].accessrole', '', '', '', 'open_login'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_file35[0].displaytype', '', '', '', 'preview'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_file35[0].filename', '', '', '', 'test.jpg'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_file35[0].format', '', '', '', 'image/jpeg'],
        )
        pub_date = props.pop()
        assert_equal(
            pub_date[:-1],
            ['.metadata.pubdate', '', '', ''],
        )
        assert_true(
            re.match(r'[0-9]+\-[0-9]+\-[0-9]+', pub_date[-1])
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_access_rights4.subitem_access_right', '', '', '', 'restricted access'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_creator2[0].creatorNames[0].creatorName', '', '', '', '情報太郎'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_creator2[0].creatorNames[0].creatorNameLang', '', '', '', 'ja'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_creator2[0].creatorNames[1].creatorName', '', '', '', 'Taro Joho'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_creator2[0].creatorNames[1].creatorNameLang', '', '', '', 'en'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_creator2[0].nameIdentifiers[0].nameIdentifierScheme', '', '', '', 'e-Rad_Researcher'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_creator2[0].nameIdentifiers[0].nameIdentifierURI', '', '', '', '22222'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_description9[0].subitem_description', '', '', '', 'TEST DESCRIPTION'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_description9[0].subitem_description_language', '', '', '', 'en'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_description9[0].subitem_description_type', '', '', '', 'Abstract'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_description9[1].subitem_description', '', '', '', 'テスト説明'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_description9[1].subitem_description_language', '', '', '', 'ja'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_description9[1].subitem_description_type', '', '', '', 'Abstract'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[0].contributorNames[0].contributorName', '', '', '', 'National Institute of Informatics Hitotsubashi TEL: XX-XXXX-XXXX E-Mail: dummy@test.rcos.nii.ac.jp'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[0].contributorNames[0].lang', '', '', '', 'en'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[0].contributorNames[0].nameType', '', '', '', 'Organizational'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[0].contributorType', '', '', '', 'ContactPerson'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[0].contributorNames[1].contributorName', '', '', '', '国立情報学研究所 一ツ橋 TEL: XX-XXXX-XXXX E-Mail: dummy@test.rcos.nii.ac.jp'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[0].contributorNames[1].lang', '', '', '', 'ja'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[0].contributorNames[1].nameType', '', '', '', 'Organizational'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[1].contributorNames[0].contributorName', '', '', '', 'Hanako Joho'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[1].contributorNames[0].lang', '', '', '', 'en'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[1].contributorType', '', '', '', 'DataManager'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[1].contributorNames[1].contributorName', '', '', '', '情報花子'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[1].contributorNames[1].lang', '', '', '', 'ja'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[1].nameIdentifiers[0].nameIdentifierScheme', '', '', '', 'e-Rad_Researcher'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[1].nameIdentifiers[0].nameIdentifierURI', '', '', '', '11111'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_rights6[0].subitem_rights', '', '', '', 'Test for license'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_rights6[0].subitem_rights_language', '', '', '', 'en'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_rights6[1].subitem_rights', '', '', '', 'ライセンスのテスト'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_rights6[1].subitem_rights_language', '', '', '', 'ja'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_rights6[2].subitem_rights', '', '', '', '無償'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_rights6[2].subitem_rights_language', '', '', '', 'ja'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_rights6[3].subitem_rights', '', '', '', 'free'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_rights6[3].subitem_rights_language', '', '', '', 'en'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_rights6[4].subitem_rights', '', '', '', 'CC0 1.0 Universal'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_rights6[4].subitem_rights_language', '', '', '', 'en'],
        )
        assert_equal(
            props.pop(),
            [
                '.metadata.item_30002_rights6[4].subitem_rights_resource',
                '',
                '',
                '',
                'https://creativecommons.org/publicdomain/zero/1.0/deed.en',
            ],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_subject8[0].subitem_subject', '', '', '', 'Life Science'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_subject8[0].subitem_subject_language', '', '', '', 'en'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_subject8[0].subitem_subject_scheme', '', '', '', 'e-Rad_field'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_subject8[1].subitem_subject', '', '', '', 'ライフサイエンス'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_subject8[1].subitem_subject_language', '', '', '', 'ja'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_subject8[1].subitem_subject_scheme', '', '', '', 'e-Rad_field'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_resource_type13.resourcetype', '', '', '', 'experimental data'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[2].contributorNames[0].contributorName', '', '', '', 'National Institute of Informatics'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[2].contributorNames[0].lang', '', '', '', 'en'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[2].contributorType', '', '', '', 'HostingInstitution'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[2].nameIdentifiers[0].nameIdentifierScheme', '', '', '', 'ROR'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[2].nameIdentifiers[0].nameIdentifierURI', '', '', '', 'https://ror.org/04ksd4g47'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[2].contributorNames[1].contributorName', '', '', '', '国立情報学研究所'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_contributor3[2].contributorNames[1].lang', '', '', '', 'ja'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_title0[0].subitem_title', '', '', '', 'TEST DATA'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_title0[0].subitem_title_language', '', '', '', 'en'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_title0[1].subitem_title', '', '', '', 'テストデータ'],
        )
        assert_equal(
            props.pop(),
            ['.metadata.item_30002_title0[1].subitem_title_language', '', '', '', 'ja'],
        )
        assert_equal(
            props.pop(),
            ['#.id', '#ID', '#', '#', ''],
        )
        assert_equal(
            props.pop(),
            ['.uri', 'URI', '', '', ''],
        )
        assert_equal(
            props.pop(),
            ['.cnri', '.CNRI', '', '', ''],
        )
        assert_equal(
            props.pop(),
            ['.doi_ra', '.DOI_RA', '', '', ''],
        )
        assert_equal(
            props.pop(),
            ['.doi', '.DOI', '', '', ''],
        )
        assert_equal(
            props.pop(),
            ['.edit_mode', 'Keep/Upgrade Version', '', 'Required', 'Keep'],
        )
