import pytest

from dataverse import Dataverse, Dataset, DataverseFile

from addons.dataverse.tests.utils import (
    create_mock_dataverse,
    create_mock_dataset,
    create_mock_draft_file,
    create_mock_connection,
    DataverseAddonTestCase,
)

pytestmark = pytest.mark.django_db


class TestUtils(DataverseAddonTestCase):

    def test_mock_connection(self):
        mock_connection = create_mock_connection()
        assert mock_connection.token == 'snowman-frosty'
        assert len(mock_connection.get_dataverses()) == 3
        assert isinstance(mock_connection.get_dataverses()[0], Dataverse)
        assert (
            mock_connection.get_dataverse(mock_connection.get_dataverses()[1].alias)
            == mock_connection.get_dataverses()[1]
        )

    def test_mock_dataverse(self):
        mock_dv = create_mock_dataverse('Example 1')
        assert mock_dv.title == 'Example 1'
        assert mock_dv.is_published
        assert mock_dv.alias == 'ALIAS1'
        assert len(mock_dv.get_datasets()) == 3
        assert isinstance(mock_dv.get_datasets()[0], Dataset)
        assert mock_dv.get_dataset_by_doi(mock_dv.get_datasets()[1].doi) == mock_dv.get_datasets()[1]

    def test_mock_dataset(self):
        dataset_id = 'DVN/23456'
        doi = f'doi:12.3456/{dataset_id}'
        mock_dataset = create_mock_dataset(dataset_id)
        assert mock_dataset.doi == doi
        assert mock_dataset.citation == f'Example Citation for {dataset_id}'
        assert mock_dataset.title == f'Example ({dataset_id})'
        assert mock_dataset.doi == doi
        assert mock_dataset.get_state() == 'DRAFT'
        assert len(mock_dataset.get_files()) == 1
        assert not mock_dataset.get_files()[0].is_published
        assert mock_dataset.get_files(published=True)[0].is_published
        assert not mock_dataset.get_file('name.txt').is_published
        assert mock_dataset.get_file('name.txt', published=True).is_published
        assert not mock_dataset.get_file_by_id('123').is_published
        assert mock_dataset.get_file_by_id('123', published=True).is_published

    def test_mock_dvn_file(self):
        fid = '65432'
        mock_file = create_mock_draft_file(fid)
        assert mock_file.name == 'file.txt'
        assert mock_file.id == fid
        assert isinstance(mock_file, DataverseFile)
