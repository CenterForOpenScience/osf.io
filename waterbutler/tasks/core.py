import os
import pickle
import asyncio
import functools

from celery.backends.base import DisabledBackend

from waterbutler.tasks import app
from waterbutler.tasks import settings
from waterbutler.tasks import exceptions


def ensure_event_loop():
    """Ensure the existance of an eventloop
    Useful for contexts where get_event_loop() may
    raise an exception.
    :returns: The new event loop
    :rtype: BaseEventLoop
    """
    try:
        return asyncio.get_event_loop()
    except (AssertionError, RuntimeError):
        asyncio.set_event_loop(asyncio.new_event_loop())

    # Note: No clever tricks are used here to dry up code
    # This avoids an infinite loop if settings the event loop ever fails
    return asyncio.get_event_loop()


def __coroutine_unwrapper(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return ensure_event_loop().run_until_complete(func(*args, **kwargs))
    wrapped.as_async = func
    return wrapped


@asyncio.coroutine
def backgrounded(func, *args, **kwargs):
    """Runs the given function with the given arguments in
    a background thread
    """
    loop = asyncio.get_event_loop()
    if asyncio.iscoroutinefunction(func):
        func = __coroutine_unwrapper(func)

    return (yield from loop.run_in_executor(
        None,  # None uses the default executer, ThreadPoolExecuter
        functools.partial(func, *args, **kwargs)
    ))

def backgroundify(func):
    @asyncio.coroutine
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return (yield from backgrounded(func, *args, **kwargs))
    return wrapped


def adhoc_file_backend(func, was_bound=False, basepath=None):
    basepath = basepath or settings.ADHOC_BACKEND_PATH

    @functools.wraps(func)
    def wrapped(task, *args, **kwargs):
        if was_bound:
            args = (task,) + args

        try:
            result = func(*args, **kwargs)
        except Exception as e:
            result = e

        with open(os.path.join(basepath, task.request.id), 'wb') as result_file:
            pickle.dump(result, result_file)

        if isinstance(result, Exception):
            raise result
        return result
    return wrapped


def celery_task(func, *args, **kwargs):
    """A wrapper around Celery.task.
    When the wrapped method is called it will be called using
    Celery's Task.delay function and run in a background thread
    """
    task_func = __coroutine_unwrapper(func)

    if isinstance(app.backend, DisabledBackend):
        task_func = adhoc_file_backend(
            task_func,
            was_bound=kwargs.pop('bind', False)
        )
        kwargs['bind'] = True

    task = app.task(task_func, **kwargs)
    task.adelay = backgroundify(task.delay)

    return task


@backgroundify
@asyncio.coroutine
def wait_on_celery(result, interval=None, timeout=None, basepath=None):
    timeout = timeout or settings.WAIT_TIMEOUT
    interval = interval or settings.WAIT_INTERVAL
    basepath = basepath or settings.ADHOC_BACKEND_PATH

    waited = 0

    while True:
        if isinstance(app.backend, DisabledBackend):
            try:
                with open(os.path.join(basepath, result.id), 'rb') as result_file:
                    data = pickle.load(result_file)
                if isinstance(data, Exception):
                    raise data
                return data
            except FileNotFoundError:
                pass
        else:
            if result.ready():
                if result.failed():
                    raise result.result
                return result.result

        if waited > timeout:
            raise exceptions.WaitTimeOutError
        yield from asyncio.sleep(interval)
        waited += interval
