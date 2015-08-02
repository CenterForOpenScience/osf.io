from nose import SkipTest
from functools import wraps


def requires_module(module):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                __import__(module)
            except ImportError:
                raise SkipTest()
            return fn(*args, **kwargs)
        return wrapper
    return decorator


class PatchedContext(object):
    """ Create a context with multiple patches.

    some_useful_patches = PatchContext(
        method_one = mock.patch('some.far.away.method_one'),
        method_two = mock.patch('some.other.method'),
    )

    with some_useful_patches as patches:
        run_tests()
        patches.get('method_one').assert_called_once_with('something')

    """
    def __init__(self, *args, **kwargs):
        self.mocks = []
        self.named_mocks = {}
        self.patches = args
        self.named_patches = kwargs

    def __enter__(self):
        for patch in self.patches:
            self.mocks.append(patch.start())

        for name, patch in self.named_patches.iteritems():
            self.named_mocks.update({name: patch.start()})

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for patch in self.patches:
            patch.stop()

        for patch in self.named_patches.values():
            patch.stop()

    def get_named_patch(self, name):
        return self.named_patches.get(name)

    def get_named_mock(self, name):
        return self.named_mocks.get(name)
