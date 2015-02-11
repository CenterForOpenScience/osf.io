import mock
import time
import unittest
from nose.tools import *  # noqa

from framework.render import core
from framework.render import exceptions


class TestRenderIsHappening(unittest.TestCase):

    @mock.patch('framework.render.core.os.path.isfile')
    def test_cache_exists_is_true(self, mock_isfile):
        mock_isfile.return_value = True
        assert_true(core.render_is_done_or_happening('path', 'path'))

    @mock.patch('framework.render.core.os.path.isfile')
    def test_nothing_exists(self, mock_isfile):
        mock_isfile.return_value = False
        assert_false(core.render_is_done_or_happening('path', 'path'))

    @mock.patch('framework.render.core.os.remove')
    @mock.patch('framework.render.core.os.path.isfile')
    @mock.patch('framework.render.core.os.path.getmtime')
    def test_old_temp(self, mockmtime, mock_isfile, mock_remove):
        mockmtime.return_value = 0
        mock_isfile.side_effect = [False, True]

        assert_false(core.render_is_done_or_happening('path', 'path'))

    @mock.patch('framework.render.core.os.remove')
    @mock.patch('framework.render.core.os.path.isfile')
    @mock.patch('framework.render.core.os.path.getmtime')
    def test_temp_newish(self, mockmtime, mock_isfile, mock_remove):
        mockmtime.return_value = time.time()
        mock_isfile.side_effect = [False, True]

        assert_true(core.render_is_done_or_happening('path', 'path'))


@mock.patch('__builtin__.open')
@mock.patch('framework.render.core.requests.get')
class TestSaveOrError(unittest.TestCase):

    @mock.patch('framework.render.core.error_message_or_exception')
    def test_bad_response(self, mock_eme, mock_request, mock_file):
        mock_request.return_value = mock.Mock(ok=False, status_code=418)

        core.save_to_file_or_error('test', 'test')

        mock_request.assert_called_once_with('test', stream=True)
        mock_eme.assert_called_once_with(418, dest_path='test', download_url='test')

    @mock.patch('framework.render.core.error_message_or_exception')
    def test_good_response(self, mock_eme, mock_request, mock_file):
        mock_request.return_value = mock.MagicMock(ok=True)

        core.save_to_file_or_error('test', 'test')

        assert_false(mock_eme.called)
        mock_request.assert_called_once_with('test', stream=True)

    def test_bad_response_raises(self, mock_request, mock_file):
        mock_request.return_value = mock.Mock(ok=False, status_code=418)

        with assert_raises(exceptions.RenderFailureException):
            core.save_to_file_or_error('test', 'test')

        mock_request.assert_called_once_with('test', stream=True)
