from nose.tools import (
    assert_equal, assert_true, assert_false, assert_is_instance
)
import pytest

from dataverse import Dataverse, Dataset, DataverseFile

from addons.dataverse.tests.utils import (
    create_mock_dataverse, create_mock_dataset, create_mock_draft_file,
    create_mock_connection, DataverseAddonTestCase,
)

pytestmark = pytest.mark.django_db


class TestUtils(DataverseAddonTestCase):

    def test_mock_connection(self):
        mock_connection = create_mock_connection()
        assert_equal(mock_connection.token, 'snowman-frosty')
        assert_equal(len(mock_connection.get_dataverses()), 3)
        assert_is_instance(mock_connection.get_dataverses()[0], Dataverse)
        assert_equal(
            mock_connection.get_dataverse(mock_connection.get_dataverses()[1].alias),
            mock_connection.get_dataverses()[1],
        )

    def test_mock_dataverse(self):
        mock_dv = create_mock_dataverse('Example 1')
        assert_equal(mock_dv.title, 'Example 1')
        assert_true(mock_dv.is_published)
        assert_equal(mock_dv.alias, 'ALIAS1')
        assert_equal(len(mock_dv.get_datasets()), 3)
        assert_is_instance(mock_dv.get_datasets()[0], Dataset)
        assert_equal(mock_dv.get_dataset_by_doi(mock_dv.get_datasets()[1].doi),
                     mock_dv.get_datasets()[1])

    def test_mock_dataset(self):
        dataset_id = 'DVN/23456'
        doi = 'doi:12.3456/{0}'.format(dataset_id)
        mock_dataset = create_mock_dataset(dataset_id)
        assert_equal(mock_dataset.doi, doi)
        assert_equal(mock_dataset.citation,
                     'Example Citation for {0}'.format(dataset_id))
        assert_equal(mock_dataset.title, 'Example ({0})'.format(dataset_id))
        assert_equal(mock_dataset.doi, doi)
        assert_equal(mock_dataset.get_state(), 'DRAFT')
        assert_equal(len(mock_dataset.get_files()), 1)
        assert_false(mock_dataset.get_files()[0].is_published)
        assert_true(mock_dataset.get_files(published=True)[0].is_published)
        assert_false(mock_dataset.get_file('name.txt').is_published)
        assert_true(mock_dataset.get_file('name.txt', published=True).is_published)
        assert_false(mock_dataset.get_file_by_id('123').is_published)
        assert_true(mock_dataset.get_file_by_id('123', published=True).is_published)

    def test_mock_dvn_file(self):
        fid = '65432'
        mock_file = create_mock_draft_file(fid)
        assert_equal(mock_file.name, 'file.txt')
        assert_equal(mock_file.id, fid)
        assert_is_instance(mock_file, DataverseFile)
