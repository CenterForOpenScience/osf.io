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
            ['.file_path[0]', '.ファイルパス[0]', '', 'Allow Multiple', 'files/test.jpg'],
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
            ['.file_path[0]', '.ファイルパス[0]', '', 'Allow Multiple', 'files/test.jpg'],
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

    def test_write_ro_crate_json_full(self):
        buf = io.StringIO()
        index = mock.MagicMock()
        index.identifier = '1000'
        index.title = 'TITLE'
        node_id = 'rvm3q'
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

        schema.write_ro_crate_json(
            self.user,
            buf,
            index,
            files,
            target_schema._id,
            [file_metadata],
            [project_metadata],
            node_id
        )

        logger.info(f'JSON: {buf.getvalue()}')
        expected = '''{
  "@context": [
    "https://w3id.org/ro/crate/1.1/context",
    "http://purl.org/wk/v1/wk-context.jsonld",
    {
      "ams:analysisType": "https://purl.org/rdm/ontology/analysisType",
      "ams:descriptionOfExperimentalCondition": "https://purl.org/rdm/ontology/descriptionOfExperimentalCondition",
      "ams:purposeOfExperiment": "https://purl.org/rdm/ontology/purposeOfExperiment",
      "ams:analysisOtherType": "https://purl.org/rdm/ontology/analysisOtherType",
      "ams:anonymousProcessing": "https://purl.org/rdm/ontology/anonymousProcessing",
      "ams:availabilityOfCommercialUse": "https://purl.org/rdm/ontology/availabilityOfCommercialUse",
      "ams:conflictOfInterest": "https://purl.org/rdm/ontology/conflictOfInterest",
      "ams:conflictOfInterestName": "https://purl.org/rdm/ontology/conflictOfInterestName",
      "ams:consentForProvisionToAThirdParty": "https://purl.org/rdm/ontology/consentForProvisionToAThirdParty",
      "ams:dataPolicyFree": "https://purl.org/rdm/ontology/dataPolicyFree",
      "ams:ethicsReviewCommitteeApproval": "https://purl.org/rdm/ontology/ethicsReviewCommitteeApproval",
      "ams:icIsNo": "https://purl.org/rdm/ontology/icIsNo",
      "ams:identifier": "https://purl.org/rdm/ontology/identifier",
      "ams:industrialUse": "https://purl.org/rdm/ontology/industrialUse",
      "ams:informedConsent": "https://purl.org/rdm/ontology/informedConsent",
      "ams:license": "https://purl.org/rdm/ontology/license",
      "ams:namesToBeIncludedInTheAcknowledgments": "https://purl.org/rdm/ontology/namesToBeIncludedInTheAcknowledgments",
      "ams:necessityOfContactAndPermission": "https://purl.org/rdm/ontology/necessityOfContactAndPermission",
      "ams:necessityOfIncludingInAcknowledgments": "https://purl.org/rdm/ontology/necessityOfIncludingInAcknowledgments",
      "ams:otherConditionsOrSpecialNotes": "https://purl.org/rdm/ontology/otherConditionsOrSpecialNotes",
      "ams:overseasOfferings": "https://purl.org/rdm/ontology/overseasOfferings",
      "ams:projectId": "https://purl.org/rdm/ontology/projectId",
      "ams:repository": "https://purl.org/rdm/ontology/repository",
      "ams:repositoryId": "https://purl.org/rdm/ontology/repositoryId",
      "ams:repositoryInfo": "https://purl.org/rdm/ontology/repositoryInfo",
      "ams:targetTypeOfAcquiredData": "https://purl.org/rdm/ontology/targetTypeOfAcquiredData",
      "ams:existExternalMetadata": "https://purl.org/rdm/ontology/existExternalMetadata",
      "ams:externalMetadataFiles": "https://purl.org/rdm/ontology/externalMetadataFiles",
      "rdm:Dataset": "https://purl.org/rdm/ontology/Dataset",
      "rdm:AccessRights": "https://purl.org/rdm/ontology/AccessRights",
      "rdm:MetadataDocument": "https://purl.org/rdm/ontology/MetadataDocument",
      "rdm:field": "https://purl.org/rdm/ontology/field",
      "rdm:keywords": "https://purl.org/rdm/ontology/keywords",
      "rdm:metadataFiles": "https://purl.org/rdm/ontology/metadataFiles",
      "rdm:project": "https://purl.org/rdm/ontology/project",
      "rdm:name": "https://purl.org/rdm/ontology/name",
      "dc:type": "http://purl.org/dc/elements/1.1/type",
      "jpcoar:addtionalType": "https://github.com/JPCOAR/schema/blob/master/2.0/#addtionalType"
    },
    {
      "ams": "https://purl.org/rdm/ontology/"
    },
    {
      "wk": "https://purl.org/rdm/ontology/"
    },
    {
      "rdm": "https://purl.org/rdm/ontology/"
    },
    {
      "odrl": "http://www.w3.org/ns/odrl.jsonld"
    },
    {
      "dc": "http://purl.org/dc/elements/1.1/"
    },
    {
      "jpcoar": "https://github.com/JPCOAR/schema/blob/master/2.0/"
    },
    {
      "datacite": "http://datacite.org/schema/kernel-4"
    }
  ],
  "@graph": [
    {
      "fundingReference": [
        {
          "@id": "_:jpcoar_fundingReference1"
        }
      ],
      "@id": "./",
      "@type": [
        "Dataset",
        "rdm:Dataset"
      ],
      "conformsTo": {
        "@id": "https://w3id.org/ro/crate/1.1"
      },
      "description": "TEST DESCRIPTION",
      "name": "TEST DATA",
      "wk:index": "1000",
      "wk:publishStatus": "private",
      "rdm:accessRightsInformation": [
        {
          "@id": "_:rdm_AccessRights1"
        }
      ],
      "creator": [
        {
          "@id": "_:Person1"
        }
      ],
      "rdm:description": {
        "@id": "_:Thing1"
      },
      "contributor": [
        {
          "@id": "_:Organization1"
        },
        {
          "@id": "_:Person2"
        },
        {
          "@id": "_:Organization2"
        }
      ],
      "rdm:licenseInformation": [
        {
          "@id": "_:rdm_License1"
        },
        {
          "@id": "_:rdm_License2"
        },
        {
          "@id": "_:rdm_License3"
        }
      ],
      "license": {
        "@id": "_:rdm_License4"
      },
      "rdm:field": [
        {
          "@id": "_:Thing2"
        }
      ],
      "dc:type": "experimental data",
      "rdm:name": {
        "@id": "_:Thing3"
      }
    },
    {
      "@type": "File",
      "encodingFormat": "image/jpeg",
      "name": "test.jpg",
      "@id": "_:File1"
    },
    {
      "@type": "Organization",
      "additionalType": {
        "@id": "https://github.com/JPCOAR/schema/blob/master/2.0/#ContactPerson"
      },
      "name": "National Institute of Informatics TEL: XX-XXXX-XXXX E-Mail: dummy@test.rcos.nii.ac.jp",
      "rdm:name": [
        {
          "@id": "_:PropertyValue11"
        },
        {
          "@id": "_:PropertyValue12"
        }
      ],
      "@id": "_:Organization1"
    },
    {
      "@type": "Organization",
      "additionalType": {
        "@id": "https://github.com/JPCOAR/schema/blob/master/2.0/#HostingInstitution"
      },
      "name": "National Institute of Informatics",
      "rdm:name": [
        {
          "@id": "_:PropertyValue15"
        },
        {
          "@id": "_:PropertyValue16"
        }
      ],
      "identifier": {
        "@id": "_:jpcoar_nameIdentifierType2"
      },
      "@id": "_:Organization2"
    },
    {
      "@type": "Person",
      "identifier": [
        {
          "@id": "_:jpcoar_nameIdentifierType1"
        }
      ],
      "name": "Taro Joho",
      "rdm:name": [
        {
          "@id": "_:PropertyValue7"
        },
        {
          "@id": "_:PropertyValue8"
        }
      ],
      "@id": "_:Person1"
    },
    {
      "@type": "Person",
      "additionalType": {
        "@id": "https://github.com/JPCOAR/schema/blob/master/2.0/#DataManager"
      },
      "name": "Hanako Joho",
      "rdm:name": [
        {
          "@id": "_:PropertyValue13"
        },
        {
          "@id": "_:PropertyValue14"
        }
      ],
      "@id": "_:Person2"
    },
    {
      "@type": "PropertyValue",
      "language": "en",
      "value": "Test Project",
      "@id": "_:PropertyValue1"
    },
    {
      "@type": "PropertyValue",
      "language": "ja",
      "value": "テスト説明",
      "@id": "_:PropertyValue10"
    },
    {
      "@type": "PropertyValue",
      "language": "en",
      "value": "National Institute of Informatics Hitotsubashi TEL: XX-XXXX-XXXX E-Mail: dummy@test.rcos.nii.ac.jp",
      "@id": "_:PropertyValue11"
    },
    {
      "@type": "PropertyValue",
      "language": "ja",
      "value": "国立情報学研究所 一ツ橋 TEL: XX-XXXX-XXXX E-Mail: dummy@test.rcos.nii.ac.jp",
      "@id": "_:PropertyValue12"
    },
    {
      "@type": "PropertyValue",
      "language": "en",
      "value": "Hanako Joho",
      "@id": "_:PropertyValue13"
    },
    {
      "@type": "PropertyValue",
      "language": "ja",
      "value": "情報花子",
      "@id": "_:PropertyValue14"
    },
    {
      "@type": "PropertyValue",
      "language": "en",
      "value": "National Institute of Informatics",
      "@id": "_:PropertyValue15"
    },
    {
      "@type": "PropertyValue",
      "language": "ja",
      "value": "国立情報学研究所",
      "@id": "_:PropertyValue16"
    },
    {
      "@type": "PropertyValue",
      "language": "en",
      "value": "CC0 1.0 Universal",
      "@id": "_:PropertyValue17"
    },
    {
      "@type": "PropertyValue",
      "language": "en",
      "name": "e-Rad_field",
      "value": "Life Science",
      "@id": "_:PropertyValue18"
    },
    {
      "@type": "PropertyValue",
      "language": "ja",
      "name": "e-Rad_field",
      "value": "ライフサイエンス",
      "@id": "_:PropertyValue19"
    },
    {
      "@type": "PropertyValue",
      "language": "ja",
      "value": "テストプロジェクト",
      "@id": "_:PropertyValue2"
    },
    {
      "@type": "PropertyValue",
      "language": "en",
      "value": "TEST DATA",
      "@id": "_:PropertyValue20"
    },
    {
      "@type": "PropertyValue",
      "language": "ja",
      "value": "テストデータ",
      "@id": "_:PropertyValue21"
    },
    {
      "@type": "PropertyValue",
      "language": "en",
      "value": "Japan Science and Technology Agency(JST)",
      "@id": "_:PropertyValue3"
    },
    {
      "@type": "PropertyValue",
      "language": "ja",
      "value": "国立研究開発法人科学技術振興機構(JST)",
      "@id": "_:PropertyValue4"
    },
    {
      "@type": "PropertyValue",
      "language": "en",
      "value": "Test Program",
      "@id": "_:PropertyValue5"
    },
    {
      "@type": "PropertyValue",
      "language": "ja",
      "value": "テストプログラム",
      "@id": "_:PropertyValue6"
    },
    {
      "@type": "PropertyValue",
      "language": "ja",
      "value": "情報太郎",
      "@id": "_:PropertyValue7"
    },
    {
      "@type": "PropertyValue",
      "language": "en",
      "value": "Taro Joho",
      "@id": "_:PropertyValue8"
    },
    {
      "@type": "PropertyValue",
      "language": "en",
      "value": "TEST DESCRIPTION",
      "@id": "_:PropertyValue9"
    },
    {
      "@type": "Thing",
      "value": [
        {
          "@id": "_:PropertyValue9"
        },
        {
          "@id": "_:PropertyValue10"
        }
      ],
      "@id": "_:Thing1"
    },
    {
      "@type": "Thing",
      "value": [
        {
          "@id": "_:PropertyValue18"
        },
        {
          "@id": "_:PropertyValue19"
        }
      ],
      "@id": "_:Thing2"
    },
    {
      "@type": "Thing",
      "value": [
        {
          "@id": "_:PropertyValue20"
        },
        {
          "@id": "_:PropertyValue21"
        }
      ],
      "@id": "_:Thing3"
    },
    {
      "@type": "jpcoar:awardNumber",
      "jpcoar:awardNumberType": "JGN",
      "value": "JP123456",
      "@id": "_:jpcoar_awardNumber1"
    },
    {
      "@type": "jpcoar:funderIdentifier",
      "jpcoar:funderIdentifierType": "e-Rad_funder",
      "value": "JST",
      "@id": "_:jpcoar_funderIdentifier1"
    },
    {
      "@type": "jpcoar:fundingReference",
      "jpcoar:awardNumber": {
        "@id": "_:jpcoar_awardNumber1"
      },
      "jpcoar:awardTitle": [
        {
          "@id": "_:PropertyValue1"
        },
        {
          "@id": "_:PropertyValue2"
        }
      ],
      "jpcoar:funderIdentifier": {
        "@id": "_:jpcoar_funderIdentifier1"
      },
      "jpcoar:funderName": [
        {
          "@id": "_:PropertyValue3"
        },
        {
          "@id": "_:PropertyValue4"
        }
      ],
      "jpcoar:fundingStreamIdentifier": {
        "@id": "_:jpcoar_fundingStreamIdentifier1"
      },
      "jpcoar:fundingStream": [
        {
          "@id": "_:PropertyValue5"
        },
        {
          "@id": "_:PropertyValue6"
        }
      ],
      "@id": "_:jpcoar_fundingReference1"
    },
    {
      "@type": "jpcoar:fundingStreamIdentifier",
      "jpcoar:fundingStreamIdentifierType": "JGN_fundingStream",
      "value": "JPTEST",
      "@id": "_:jpcoar_fundingStreamIdentifier1"
    },
    {
      "@type": "jpcoar:nameIdentifierType",
      "jpcoar:nameIdentifierScheme": "e-Rad_Researcher",
      "value": "22222",
      "@id": "_:jpcoar_nameIdentifierType1"
    },
    {
      "@type": "jpcoar:nameIdentifierType",
      "jpcoar:nameIdentifierScheme": "ROR",
      "value": "https://ror.org/04ksd4g47",
      "@id": "_:jpcoar_nameIdentifierType2"
    },
    {
      "@type": "rdm:AccessRights",
      "rdm:conditionOfAccess": {
        "@id": "TODO"
      },
      "@id": "_:rdm_AccessRights1"
    },
    {
      "@type": "rdm:License",
      "memo": "TODO",
      "subitem_rights": "Test for license",
      "subitem_rights_language": "en",
      "@id": "_:rdm_License1"
    },
    {
      "@type": "rdm:License",
      "memo": "TODO",
      "subitem_rights": "ライセンスのテスト",
      "subitem_rights_language": "ja",
      "@id": "_:rdm_License2"
    },
    {
      "@type": "rdm:License",
      "ams:dataPolicyFree": "free",
      "@id": "_:rdm_License3"
    },
    {
      "@type": [
        "rdm:License",
        "CreativeWork"
      ],
      "name": "CC0 1.0 Universal",
      "rdm:name": [
        {
          "@id": "_:PropertyValue17"
        }
      ],
      "rdm:url": "https://creativecommons.org/publicdomain/zero/1.0/deed.en",
      "@id": "_:rdm_License4"
    },
    {
      "@id": "ro-crate-metadata.json",
      "@type": "CreativeWork",
      "about": {
        "@id": "./"
      },
      "conformsTo": {
        "@id": "https://w3id.org/ro/crate/1.1"
      }
    }
  ]
}
'''
        actual_json = json.loads(buf.getvalue())
        for item in actual_json['@graph']:
            item.pop('wk:feedbackMail', None)
            item.pop('datePublished', None)
        assert_equal(actual_json, json.loads(expected))
