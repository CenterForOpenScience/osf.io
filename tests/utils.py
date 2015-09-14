from nose import SkipTest
from nose.tools import assert_equal, assert_not_equal
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


def assert_logs(log_action, node_key, index=-1):
    """A decorator to ensure a log is added during a unit test.
    :param str log_action: NodeLog action
    :param str node_key: key to get Node instance from self
    :param int index: list index of log to check against

    Example usage:
    @assert_logs(NodeLog.UPDATED_FIELDS, 'node')
    def test_update_node(self):
        self.node.update({'title': 'New Title'}, auth=self.auth)

    TODO: extend this decorator to check log param correctness?
    """
    def outer_wrapper(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            node = getattr(self, node_key)
            last_log = node.logs[-1]
            func(self, *args, **kwargs)
            node.reload()
            new_log = node.logs[index]
            assert_not_equal(last_log._id, new_log._id)
            assert_equal(new_log.action, log_action)
            node.save()
        return wrapper
    return outer_wrapper

def assert_not_logs(log_action, node_key, index=-1):
    def outer_wrapper(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            node = getattr(self, node_key)
            last_log = node.logs[-1]
            func(self, *args, **kwargs)
            node.reload()
            new_log = node.logs[index]
            assert_not_equal(new_log.action, log_action)
            assert_equal(last_log._id, new_log._id)
            node.save()
        return wrapper
    return outer_wrapper
