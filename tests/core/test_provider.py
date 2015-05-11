import pytest

from tests.core import utils
from tests.utils import async
from waterbutler.core import exceptions


@pytest.fixture
def provider1():
    return utils.MockProvider1({'user': 'name'}, {'pass': 'word'}, {})

@pytest.fixture
def provider2():
    return utils.MockProvider2({'user': 'name'}, {'pass': 'phrase'}, {})


class TestCopy:

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
