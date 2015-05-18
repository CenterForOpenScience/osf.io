import pytest
import functools
from urllib import parse

from waterbutler.core import exceptions
from waterbutler.core.path import WaterButlerPath
from waterbutler.core.path import WaterButlerPathPart


class EncodedPathPart:
    DECODE = parse.unquote
    ENCODE = functools.partial(parse.quote, safe='')

class EncodedPath:
    PART_CLASS = EncodedPathPart

class TestPathPart:
    pass

class TestPath:

    def test_name(self):
        path = WaterButlerPath('/this/is/a/long/path')

        assert path.name == 'path'

    def test_parent(self):
        path = WaterButlerPath('/this/is/a/long/path')

        assert path.parent.name == 'long'
        assert path.parent == WaterButlerPath('/this/is/a/long/')

    def test_ending_slash_is_folder(self):
        assert WaterButlerPath('/this/is/folder/').is_dir is True
        assert WaterButlerPath('/this/is/folder/').is_file is False

    def test_no_ending_slash_is_file(self):
        assert WaterButlerPath('/this/is/file').is_dir is False
        assert WaterButlerPath('/this/is/file').is_file is True

    def test_is_root(self):
        assert WaterButlerPath('/').is_root is True
        assert WaterButlerPath('/this/is/folder/').is_root is False

    def test_child(self):
        path = WaterButlerPath('/this/is/a/long/')

        assert path.name == 'long'
        assert path.child('path').name == 'path'

    def test_rename(self):
        path = WaterButlerPath('/this/is/a/long/path')

        assert path.name == 'path'

        path.rename('journey')

        assert path.name == 'journey'


class TestValidation:

    def test_double_slash_is_invalid(self):
        with pytest.raises(exceptions.InvalidPathError):
            WaterButlerPath('/this//is/a/path')

    def test_must_start_with_slash(self):
        with pytest.raises(exceptions.InvalidPathError):
            WaterButlerPath('this/is/a/path')

    def test_cant_be_empty(self):
        with pytest.raises(exceptions.InvalidPathError):
            WaterButlerPath('')

    def test_cant_have_dotdot(self):
        with pytest.raises(exceptions.InvalidPathError):
            WaterButlerPath('/etc/nginx/../')
