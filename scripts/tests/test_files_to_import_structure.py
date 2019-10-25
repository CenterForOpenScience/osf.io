# -*- coding: utf-8 -*-
import mock
from tests.base import OsfTestCase
from scripts.EGAP.files_to_import_structure import action_files_by_name


class TestEGAPFilesToImportStructure(OsfTestCase):

    @mock.patch('scripts.EGAP.files_to_import_structure.os.mkdir')
    @mock.patch('scripts.EGAP.files_to_import_structure.shutil.move')
    def test_doesnt_move_nonanon_files(self, mock_move, mock_mkdir):
        action_files_by_name(
            'scripts/tests/test_files/test_nonanonymous',
            'scripts/tests/test_files/test_nonanonymous/20151016AA_PAP.pdf',
            '20151016AA_PAP.pdf'
        )
        assert not mock_mkdir.called
        assert not mock_move.called

    @mock.patch('scripts.EGAP.files_to_import_structure.os.mkdir')
    @mock.patch('scripts.EGAP.files_to_import_structure.shutil.move')
    def test_moves_anon_files(self, mock_move, mock_mkdir):
        action_files_by_name(
            'scripts/tests/test_files/test_nonanonymous',
            'scripts/tests/test_files/test_nonanonymous/imafile_Anonymous.pdf',
            'imafile_Anonymous.pdf'
        )

        mock_mkdir.assert_called_with('scripts/tests/test_files/anonymous')

        mock_move.assert_called_with(
            'scripts/tests/test_files/test_nonanonymous/imafile_Anonymous.pdf',
            'scripts/tests/test_files/anonymous/imafile_Anonymous.pdf'
        )

