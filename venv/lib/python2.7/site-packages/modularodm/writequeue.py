# -*- coding: utf-8 -*-

import logging
import collections


logger = logging.getLogger(__name__)


class WriteAction(object):

    def __init__(self, method, *args, **kwargs):
        if not callable(method):
            raise ValueError('Argument `method` must be callable')
        self.method = method
        # Note: `args` and `kwargs` must not be mutated after an action is
        # enqueued and before it is committed, else awful things can happen
        self.args = args
        self.kwargs = kwargs

    def execute(self):
        return self.method(*self.args, **self.kwargs)

    def __repr__(self):
        return '{0}(*{1}, **{2})'.format(
            self.method.__name__,
            self.args,
            self.kwargs
        )


class WriteQueue(object):

    def __init__(self):
        self.active = False
        self.actions = collections.deque()

    def start(self):
        if self.active:
            logger.warn('Already working in a write queue. Further writes '
                        'will be appended to the current queue.')
        self.active = True

    def push(self, action):
        if not self.active:
            raise ValueError('Cannot push unless queue is active')
        if not isinstance(action, WriteAction):
            raise TypeError('Argument `action` must be instance '
                            'of `WriteAction`')
        self.actions.append(action)

    def commit(self):
        if not self.active:
            raise ValueError('Cannot commit unless queue is active')
        results = []
        while self.actions:
            action = self.actions.popleft()
            results.append(action.execute())
        return results

    def clear(self):
        self.active = False
        self.actions = collections.deque()

    def __nonzero__(self):
        return bool(self.actions)


class QueueContext(object):

    def __init__(self, BaseSchema):
        self.BaseSchema = BaseSchema

    def __enter__(self):
        self.BaseSchema.start_queue()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.BaseSchema.commit_queue()
