import pytest

from tests import utils
from unittest import mock
from tests.utils import async
from waterbutler.core import exceptions


@pytest.fixture
def provider1():
    return utils.MockProvider1({'user': 'name'}, {'pass': 'word'}, {})

@pytest.fixture
def provider2():
    return utils.MockProvider2({'user': 'name'}, {'pass': 'phrase'}, {})


class TestBaseProvider:

    def test_eq(self, provider1, provider2):
        assert provider1 == provider1
        assert provider2 == provider2
        assert provider1 != provider2

    def test_serialize(self, provider1):
        assert provider1.serialized() == {
            'name': 'MockProvider1',
            'auth': {'user': 'name'},
            'settings': {},
            'credentials': {'pass': 'word'}
        }

    def test_cant_intra_move(self, provider1):
        assert provider1.can_intra_move(provider1) is False

    def test_can_intra_move(self, provider2):
        assert provider2.can_intra_move(provider2) is True

    @async
    def test_exits(self, provider1):
        ret = yield from provider1.exists('somepath')
        assert ret == {}

    @async
    def test_exits_doesnt_exist(self, provider1):
        ret = yield from provider1.exists(
            'somepath',
            throw=exceptions.MetadataError('', code=404)
        )
        assert ret is False

    @async
    def test_exits_raises_non_404(self, provider1):
        with pytest.raises(exceptions.MetadataError) as e:
            yield from provider1.exists(
                'somepath',
                throw=exceptions.MetadataError('', code=422)
            )

        assert e.value.code == 422

    @async
    def test_intra_copy_notimplemented(self, provider1):
        with pytest.raises(NotImplementedError):
            yield from provider1.intra_copy(provider1, None, None)

    @async
    def test_intra_move_notimplemented(self, provider1):
        with pytest.raises(NotImplementedError):
            yield from provider1.intra_copy(provider1, None, None)

    @async
    def test_intra_move_uses_intra_copy(self, provider1, monkeypatch):
        icopy_mock = utils.MockCoroutine()
        delete_mock = utils.MockCoroutine()
        icopy_mock.return_value = ({}, False)
        monkeypatch.setattr(provider1, 'intra_copy', icopy_mock)
        monkeypatch.setattr(provider1, 'delete', delete_mock)

        metadata, created = yield from provider1.intra_move(provider1, None, None)

        assert metadata == {}
        assert created is False
        assert delete_mock.called is True
        icopy_mock.assert_called_once_with(provider1, None, None) is True

    @async
    def test_create_folder_raises(self, provider1):
        with pytest.raises(exceptions.ProviderError) as e:
            yield from provider1.create_folder('Doesnt matter')

        assert e.value.code == 405
        assert e.value.data == {
            'message': 'Folder creation not supported.'
        }

    @async
    def test_revalidate_path_is_child(self, provider1):
        path = yield from provider1.validate_path('/this/is/a/path/')
        new_path = yield from provider1.revalidate_path(path, 'text_file.txt')

        assert new_path.is_file
        assert str(path) == str(new_path.parent)
        assert new_path.name == 'text_file.txt'
