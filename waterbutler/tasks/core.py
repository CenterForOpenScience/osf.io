import asyncio
import functools

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
    except AssertionError:
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


def backgrounded(func, *args, **kwargs):
    """Runs the given function with the given arguments in
    a background thread
    """
    loop = asyncio.get_event_loop()
    if asyncio.iscoroutinefunction(func):
        func = __coroutine_unwrapper(func)

    return (yield from loop.run_in_executor(
        None,
        functools.partial(func, *args, **kwargs)
    ))

def backgroundify(func):
    @asyncio.coroutine
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return (yield from backgrounded(func, *args, **kwargs))
    return wrapped


def celery_task(func, *args, **kwargs):
    """A wrapper around Celery.task.
    When the wrapped method is called it will be called using
    Celery's Task.delay function and run in a background thread
    """
    task = app.task(__coroutine_unwrapper(func), **kwargs)
    task.adelay = backgroundify(task.delay)

    return task


#TODO run entire task in background
@asyncio.coroutine
def wait_on_celery(result, interval=None, timeout=None):
    timeout = timeout or settings.WAIT_TIMEOUT
    interval = interval or settings.WAIT_INTERVAL

    waited = 0

    while waited < timeout:
        if (yield from backgrounded(result.ready)):
            return (yield from backgrounded(lambda: result.result))
            return result.result
        waited += interval
        yield from asyncio.sleep(interval)

    raise exceptions.WaitTimeOutError
