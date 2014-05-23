from nose.tools import *
import mock

from website.addons.dataverse.dvn.dataverse import Dataverse
from website.addons.dataverse.dvn.file import DvnFile, ReleasedFile
from website.addons.dataverse.dvn.study import Study
from website.addons.dataverse.tests.utils import create_mock_connection, \
    create_mock_dataverse, create_mock_study, DataverseAddonTestCase


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
        assert_equal(mock_connection.get_dataverses()[0].__class__, Dataverse)
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
        assert_equal(mock_dv.get_studies()[0].__class__, Study)
        assert_equal(mock_dv.get_study_by_hdl(mock_dv.get_studies()[1].get_id()),
                     mock_dv.get_studies()[1])

    def test_mock_study(self):
        sid = 'DVN/23456'
        mock_study = create_mock_study(sid)
        assert_equal(mock_study.get_id(), sid)
        assert_equal(mock_study.get_citation(),
                     'Example Citation for {0}'.format(sid))
        assert_equal(mock_study.title, 'Example ({0})'.format(sid))
        assert_equal(mock_study.doi, 'doi:12.3456/{0}'.format(sid))
        assert_equal(mock_study.get_state(), 'DRAFT')
        assert_equal(len(mock_study.get_files()), 1)
        assert_equal(mock_study.get_files()[0].__class__, DvnFile)
        assert_equal(mock_study.get_files(released=True)[0].__class__,
                     ReleasedFile)
        assert_equal(mock_study.get_file('name.txt').__class__, DvnFile)
        assert_equal(mock_study.get_file('name.txt', released=True).__class__,
                     ReleasedFile)
        assert_equal(mock_study.get_file_by_id('123').__class__, DvnFile)
        assert_equal(mock_study.get_file_by_id('123', released=True).__class__,
                     ReleasedFile)
