import datetime
import pathlib
from unittest import mock

import rdflib

from osf import models as osfdb
from osf.metadata.rdfutils import OSF, DCTERMS
from osf.metadata.tools import pls_gather_metadata_file
from osf.models.licenses import NodeLicense
from api_tests.utils import create_test_file
from osf_tests import factories
from osf_tests.metadata._utils import assert_graphs_equal
from tests.base import OsfTestCase


# a directory of metadata files that will be expected as test outputs
METADATA_SCENARIO_DIR = (
    pathlib.Path(__file__).parent  # alongside this `.py` file
    / 'expected_metadata_files'
)

BASIC_METADATA_SCENARIO = {
    OSF.Project: {
        'turtle': 'project_basic.turtle',
        'datacite-xml': 'project_basic.datacite.xml',
        'datacite-json': 'project_basic.datacite.json',
    },
    OSF.Preprint: {
        'turtle': 'preprint_basic.turtle',
        'datacite-xml': 'preprint_basic.datacite.xml',
        'datacite-json': 'preprint_basic.datacite.json',
    },
    OSF.Registration: {
        'turtle': 'registration_basic.turtle',
        'datacite-xml': 'registration_basic.datacite.xml',
        'datacite-json': 'registration_basic.datacite.json',
    },
    OSF.File: {
        'turtle': 'file_basic.turtle',
        'datacite-xml': 'file_basic.datacite.xml',
        'datacite-json': 'file_basic.datacite.json',
    },
    DCTERMS.Agent: {
        'turtle': 'user_basic.turtle',
    },
}

FULL_METADATA_SCENARIO = {
    OSF.Project: {
        'turtle': 'project_full.turtle',
        'datacite-xml': 'project_full.datacite.xml',
        'datacite-json': 'project_full.datacite.json',
    },
    OSF.Preprint: {
        'turtle': 'preprint_full.turtle',
        'datacite-xml': 'preprint_full.datacite.xml',
        'datacite-json': 'preprint_full.datacite.json',
    },
    OSF.Registration: {
        'turtle': 'registration_full.turtle',
        'datacite-xml': 'registration_full.datacite.xml',
        'datacite-json': 'registration_full.datacite.json',
    },
    OSF.File: {
        'turtle': 'file_full.turtle',
        'datacite-xml': 'file_full.datacite.xml',
        'datacite-json': 'file_full.datacite.json',
    },
    DCTERMS.Agent: {
        'turtle': 'user_full.turtle',
    },
}

EXPECTED_MEDIATYPE = {
    'turtle': 'text/turtle; charset=utf-8',
    'datacite-xml': 'application/xml',
    'datacite-json': 'application/json',
}


class OsfguidSequence:
    def __init__(self, start_str):
        self._letter = start_str[0]
        self._rest = start_str[1:]
        self._count = 0

    def __call__(self, length=5):
        self._count += 1
        return ''.join((self._letter, str(self._count), self._rest))[:length]

    def get_or_create(self, defaults=None, **kwargs):
        # avoid calling Guid.objects.get_or_create, which this patches over
        try:
            return (
                osfdb.Guid.objects.get(**kwargs),
                False,  # not created
            )
        except osfdb.Guid.DoesNotExist:
            return (
                osfdb.Guid.objects.create(
                    **kwargs,
                    **(defaults or {}),
                    _id=self(),  # use a guid from the sequence
                ),
                True  # yes created
            )


def forever_now():
    return datetime.datetime(2123, 5, 4, tzinfo=datetime.UTC)


class TestSerializers(OsfTestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()
        # patch auto-generated fields into predictable values
        osfguid_sequence = OsfguidSequence('wibble')
        for patcher in (
            mock.patch('osf.models.base.generate_guid', new=osfguid_sequence),
            mock.patch('osf.models.base.Guid.objects.get_or_create', new=osfguid_sequence.get_or_create),
            mock.patch('django.utils.timezone.now', new=forever_now),
            mock.patch('osf.models.metaschema.RegistrationSchema.absolute_api_v2_url', new='http://fake.example/schema/for/test'),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        # build test objects
        self.user = factories.AuthUserFactory(
            fullname='Person McNamington',
        )
        self.project = factories.ProjectFactory(
            is_public=True,
            creator=self.user,
            title='this is a project title!',
            description='this is a project description!',
            node_license=factories.NodeLicenseRecordFactory(
                node_license=NodeLicense.objects.get(
                    name='No license',
                ),
                year='2252',
                copyright_holders=['Me', 'You'],
            ),
        )
        self.project.set_identifier_value(
            category='doi',
            value=f'10.70102/FK2osf.io/{self.project._id}',
        )
        self.file = create_test_file(
            self.project,
            self.user,
            filename='my-file.blarg',
            size=7,
            sha256='6ac3c336e4094835293a3fed8a4b5fedde1b5e2626d9838fed50693bba00af0e',
        )
        osf_preprint_provider = factories.PreprintProviderFactory(_id='osf')
        another_provider = factories.PreprintProviderFactory(
            _id='preprovi',
            name='PP the Preprint Provider',
            doi_prefix='11.pp',
        )
        parent_subject = factories.SubjectFactory(
            _id='subjwibb',
            text='wibble',
            provider=another_provider,
            parent=None,
            bepress_subject=factories.SubjectFactory(
                _id='subjwibbb',
                text='wibbble',
                parent=None,
                provider=osf_preprint_provider,
                bepress_subject=None,
            ),
        )
        child_subject = factories.SubjectFactory(
            _id='subjwobb',
            text='wobble',
            provider=another_provider,
            parent=parent_subject,
            bepress_subject=factories.SubjectFactory(
                _id='subjwobbb',
                text='wobbble',
                parent=parent_subject.bepress_subject,
                provider=osf_preprint_provider,
                bepress_subject=None,
            ),
        )
        self.preprint = factories.PreprintFactory(
            is_public=True,
            title='this is a preprint title!',
            description='this is a preprint description!',
            project=self.project,
            creator=self.user,
            doi='11.111/something-or-other',
            provider=another_provider,
            subjects=[
                [parent_subject._id, child_subject._id],
            ],
        )
        self.registration = factories.RegistrationFactory(
            is_public=True,
            project=self.project,
            user=self.user,
            provider=factories.RegistrationProviderFactory(
                _id='regiprovi',
                name='RegiProvi the Registration Provider',
                doi_prefix='11.rp',
            ),
        )
        osfdb.GuidMetadataRecord.objects.for_guid(self.registration._id).update({
            'resource_type_general': 'StudyRegistration',
        }, auth=self.user)
        self.guid_dict = {
            OSF.Project: self.project._id,
            OSF.Preprint: self.preprint._id,
            OSF.Registration: self.registration._id,
            OSF.File: self.file.get_guid()._id,
            DCTERMS.Agent: self.user._id,
        }

    def _setUp_full(self):
        self.metadata_record = osfdb.GuidMetadataRecord.objects.for_guid(self.project._id)
        self.metadata_record.update({
            'language': 'en',
            'resource_type_general': 'Dataset',
            'funding_info': [
                {  # full funding reference:
                    'funder_name': 'Mx. Moneypockets',
                    'funder_identifier': 'https://doi.org/10.$$$$',
                    'funder_identifier_type': 'Crossref Funder ID',
                    'award_number': '10000000',
                    'award_uri': 'https://moneypockets.example/millions',
                    'award_title': 'because reasons',
                }, {  # second funding award from the same funder:
                    'funder_name': 'Mx. Moneypockets',
                    'funder_identifier': 'https://doi.org/10.$$$$',
                    'funder_identifier_type': 'Crossref Funder ID',
                    'award_number': '2000000',
                    'award_uri': 'https://moneypockets.example/millions-more',
                    'award_title': 'because reasons!',
                }, {  # no award info, just a funder:
                    'funder_name': 'Caring Fan',
                    'funder_identifier': 'https://doi.org/10.$',
                    'funder_identifier_type': 'Crossref Funder ID',
                    'award_number': '',
                    'award_uri': '',
                    'award_title': '',
                },
            ],
        }, auth=self.user)
        self.project.node_license.node_license = NodeLicense.objects.get(
            name='CC-By Attribution-NonCommercial-NoDerivatives 4.0 International',
        )
        self.project.node_license.year = '2250-2254'
        self.project.node_license.save()

    def test_serialized_metadata(self):
        self._assert_scenario(BASIC_METADATA_SCENARIO)
        self._setUp_full()
        self._assert_scenario(FULL_METADATA_SCENARIO)

    def _assert_scenario(self, scenario_dict):
        for focus_type, expected_files in scenario_dict.items():
            for format_key, filename in expected_files.items():
                osfguid = self.guid_dict[focus_type]
                gathered_file = pls_gather_metadata_file(osfguid, format_key)
                with self.subTest(focus_type=focus_type, format_key=format_key, testpath='pls_gather_metadata_file'):
                    self.assertEqual(gathered_file.mediatype, EXPECTED_MEDIATYPE[format_key])
                    # to update expected metadata, uncomment `_write_expected_file` and this
                    # next line (being careful not to leave it uncommented...) and run tests
                    # self._write_expected_file(filename, gathered_file.serialized_metadata)
                    self._assert_expected_file(filename, gathered_file.serialized_metadata)

                with self.subTest(focus_type=focus_type, format_key=format_key, testpath='metadata download'):
                    resp = self.app.get(f'/{osfguid}/metadata/?format={format_key}')
                    assert resp.status_code == 200
                    self.assertEqual(resp.status_code, 200)
                    self.assertEqual(resp.headers['Content-Type'], EXPECTED_MEDIATYPE[format_key])
                    self.assertEqual(
                        resp.headers['Content-Disposition'],
                        f'attachment; filename={gathered_file.filename}',
                    )
                    self._assert_expected_file(filename, resp.text)

    def _assert_expected_file(self, filename, actual_metadata):
        _open_mode = ('rb' if isinstance(actual_metadata, bytes) else 'r')
        with open(METADATA_SCENARIO_DIR / filename, _open_mode) as _file:
            _expected_metadata = _file.read()  # small files; read all at once
        if filename.endswith('.turtle'):
            # HACK: because the turtle serializer may output things in different order
            # TODO: stable turtle serializer (or another primitive rdf serialization)
            self._assert_equivalent_turtle(actual_metadata, _expected_metadata)
        else:
            self.assertEqual(actual_metadata, _expected_metadata)

    def _assert_equivalent_turtle(self, actual_turtle, expected_turtle):
        _actual = rdflib.Graph()
        _actual.parse(data=actual_turtle, format='turtle')
        _expected = rdflib.Graph()
        _expected.parse(data=expected_turtle, format='turtle')
        assert_graphs_equal(_actual, _expected)

    # def _write_expected_file(self, filename, expected_metadata):
    #     '''for updating expected metadata files from current serializers
    #     (be careful to check that changes are, in fact, expected)
    #     '''
    #     _open_mode = ('wb' if isinstance(expected_metadata, bytes) else 'w')
    #     with open(METADATA_SCENARIO_DIR / filename, _open_mode) as _file:
    #         _file.write(expected_metadata)
