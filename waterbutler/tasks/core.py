import asyncio
import functools

from waterbutler.tasks import app


def ensure_event_loop():
    try:
        return asyncio.get_event_loop()
    except AssertionError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    # Note: No clever tricks are used here to dry up code
    # This avoids an infinite loop if settings the event loop ever fails
    return asyncio.get_event_loop()


def __coroutine_unwrapper(func, *args, **kwargs):
    return ensure_event_loop().run_until_complete(func(*args, **kwargs))


def backgrounded(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    if asyncio.iscoroutinefunction(func):
        args = (func, ) + args
        func = __coroutine_unwrapper

    return loop.run_in_executor(
        None,
        functools.partial(func, *args, **kwargs)
    )


def celery_task(*args, **kwargs):
    func = app.task(*args, **kwargs)

    @asyncio.coroutine
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        return (yield from backgrounded(func.delay, *args, **kwargs))
    return wrapped
