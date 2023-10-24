import asyncio

from asgiref.sync import async_to_sync


def just_return_1(return_value):
    if type(return_value) is not bool:
        raise Exception
    return return_value


def just_return_2(return_value):
    if type(return_value) is not bool:
        raise Exception
    return return_value


def foo_sync(return_value_1, return_value_2):
    return just_return_1(return_value_1) and just_return_2(return_value_2)


async def bar_async(return_value_1, return_value_2):
    await asyncio.sleep(1)
    return just_return_1(return_value_1) and just_return_2(return_value_2)


def bar_async_to_sync(return_value_1, return_value_2):
    return async_to_sync(bar_async)(return_value_1, return_value_2)
