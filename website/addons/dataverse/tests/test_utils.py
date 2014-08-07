from nose.tools import *
import mock

from dataverse import Dataverse, Study, DataverseFile

from website.addons.dataverse.tests.utils import (
    create_mock_connection,
    create_mock_dataverse, create_mock_study, create_mock_draft_file,
    create_mock_released_file, DataverseAddonTestCase
)


class TestUtils(DataverseAddonTestCase):

    def test_mock_connection(self):
        # A connection with bad credentials fails
        failed_connection = create_mock_connection('wrong', 'info')
        assert_false(failed_connection)

        # A good connection has the correct parameters
        mock_connection = create_mock_connection()
        assert_equal(mock_connection.username, 'snowman')
        assert_equal(mock_connection.password, 'frosty')
        assert_equal(len(mock_connection.get_dataverses()), 3)
        assert_is_instance(mock_connection.get_dataverses()[0], Dataverse)
        assert_equal(
            mock_connection.get_dataverse(mock_connection.get_dataverses()[1].alias),
            mock_connection.get_dataverses()[1],
        )

    def test_mock_dataverse(self):
        mock_dv = create_mock_dataverse('Example 1')
        assert_equal(mock_dv.title, 'Example 1')
        assert_true(mock_dv.is_released)
        assert_equal(mock_dv.alias, 'ALIAS1')
        assert_equal(len(mock_dv.get_studies()), 3)
        assert_is_instance(mock_dv.get_studies()[0], Study)
        assert_equal(mock_dv.get_study_by_doi(mock_dv.get_studies()[1].doi),
                     mock_dv.get_studies()[1])

    def test_mock_study(self):
        study_id = 'DVN/23456'
        doi = 'doi:12.3456/{0}'.format(study_id)
        mock_study = create_mock_study(study_id)
        assert_equal(mock_study.doi, doi)
        assert_equal(mock_study.citation,
                     'Example Citation for {0}'.format(study_id))
        assert_equal(mock_study.title, 'Example ({0})'.format(study_id))
        assert_equal(mock_study.doi, doi)
        assert_equal(mock_study.get_state(), 'DRAFT')
        assert_equal(len(mock_study.get_files()), 1)
        assert_false(mock_study.get_files()[0].is_released)
        assert_true(mock_study.get_files(released=True)[0].is_released)
        assert_false(mock_study.get_file('name.txt').is_released)
        assert_true(mock_study.get_file('name.txt', released=True).is_released)
        assert_false(mock_study.get_file_by_id('123').is_released)
        assert_true(mock_study.get_file_by_id('123', released=True).is_released)

    def test_mock_dvn_file(self):
        fid = '65432'
        mock_file = create_mock_draft_file(fid)
        assert_equal(mock_file.name, 'file.txt')
        assert_equal(mock_file.id, fid)
        assert_is_instance(mock_file, DataverseFile)

