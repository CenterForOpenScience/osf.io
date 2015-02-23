import re
import asyncio

import tornado.concurrent
import tornado.ioloop


def parse_disposition_name(disposition):
    if disposition:
        match = re.search(r'filename="(.*?)"', disposition)
        return match.groups()[0] if match else None


# Running Tornado on asyncio's event loop, including 'yield from' support in request handlers
# https://gist.github.com/BeholdMyGlory/11067131
def coroutine(func):
    func = asyncio.coroutine(func)

    def decorator(*args, **kwargs):
        future = tornado.concurrent.Future()

        def future_done(f):
            try:
                future.set_result(f.result())
            except Exception as e:
                future.set_exception(e)

        asyncio.async(func(*args, **kwargs)).add_done_callback(future_done)
        return future

    return decorator


def future_wrapper(f):
    future = asyncio.Future()

    def handle_future(f):
        try:
            future.set_result(f.result())
        except Exception as e:
            future.set_exception(e)

    tornado.ioloop.IOLoop.current().add_future(f, handle_future)
    return future
