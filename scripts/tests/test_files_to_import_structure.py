# -*- coding: utf-8 -*-
import mock
from tests.base import OsfTestCase
from scripts.EGAP.files_to_import_structure import action_files_by_name


class TestEGAPFilesToImportStructure(OsfTestCase):

    @mock.patch('scripts.EGAP.files_to_import_structure.os.mkdir')
    @mock.patch('scripts.EGAP.files_to_import_structure.shutil.move')
    def test_doesnt_move_nonanon_files(self, mock_move, mock_mkdir):
        action_files_by_name(
            'scripts/tests/test_files/20151016AA/data/datatest_nonanonymous',
            'scripts/tests/test_files/20151016AA/data/test_nonanonymous/20151016AA_PAP.pdf',
            '20151016AA_PAP.pdf'
        )
        assert not mock_mkdir.called
        assert not mock_move.called

    @mock.patch('scripts.EGAP.files_to_import_structure.os.mkdir')
    @mock.patch('scripts.EGAP.files_to_import_structure.shutil.move')
    def test_moves_anon_files(self, mock_move, mock_mkdir):
        action_files_by_name(
            'scripts/tests/test_files/20151016AA/data/test_nonanonymous',
            'scripts/tests/test_files/20151016AA/data/test_nonanonymous/20151016AA_anonymous.pdf',
            '20151016AA_anonymous.pdf'
        )

        mock_mkdir.assert_called_with('scripts/tests/test_files/20151016AA/data/anonymous')

        mock_move.assert_called_with(
            'scripts/tests/test_files/20151016AA/data/test_nonanonymous/20151016AA_anonymous.pdf',
            'scripts/tests/test_files/20151016AA/data/anonymous/20151016AA_anonymous.pdf'
        )

    @mock.patch('scripts.EGAP.files_to_import_structure.os.remove')
    def test_removes_no_id(self, mock_remove):
        action_files_by_name(
            'scripts/tests/test_files/20151016AA/data/test_nonanonymous',
            'scripts/tests/test_files/20151016AA/data/test_nonanonymous/justafile.pdf',
            'justafile.pdf'
        )

        mock_remove.assert_called_with('scripts/tests/test_files/20151016AA/data/test_nonanonymous/justafile.pdf')

    @mock.patch('scripts.EGAP.files_to_import_structure.os.remove')
    def test_removes_form(self, mock_remove):

        action_files_by_name(
            'scripts/tests/test_files/20151016AA/data/test_nonanonymous',
            'scripts/tests/test_files/20151016AA/data/test_nonanonymous/20151016AA_FORM.pdf',
            '20151016AA_FORM.pdf'
        )

        mock_remove.assert_called_with('scripts/tests/test_files/20151016AA/data/test_nonanonymous/20151016AA_FORM.pdf')
