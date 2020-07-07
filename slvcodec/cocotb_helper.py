"""
Utilities to make it easy to help a family of coroutines
i.e. Kill a coroutine along with all coroutines that were forked from
there.
"""


import logging
from functools import wraps

import cocotb
from cocotb import triggers

logger = logging.getLogger(__name__)


class KilledError(Exception):
    pass


class TaskWrapper:

    def __init__(self, helper, task):
        self.helper = helper
        self.task = task

    def kill(self):
        self.helper.kill()

    def done(self):
        return self.task._finished


class FakeTaskWrapper:

    def kill(self):
        pass

    def done(self):
        return True


class TaskHelper:

    def __init__(self, name=None):
        self.child_helpers = []
        self._killed = False
        self.name = name

    @cocotb.coroutine
    async def RisingEdge(self, signal, kill_callback=None):
        await triggers.RisingEdge(signal)
        if self.killed:
            if kill_callback:
                kill_callback()
            raise KilledError

    @cocotb.coroutine
    async def ReadOnly(self, kill_callback=None):
        await triggers.ReadOnly()
        if self.killed:
            if kill_callback:
                kill_callback()
            raise KilledError

    def fork(self, needs_helper, name=None):
        if not self._killed:
            if name is None:
                name = needs_helper.__name__
            forked_helper = TaskHelper(name=name)
            self.child_helpers.append(forked_helper)
            coroutine = needs_helper(forked_helper)
            task = cocotb.fork(coroutine)
            return TaskWrapper(forked_helper, task)
        else:
            return FakeTaskWrapper()

    @cocotb.coroutine
    async def add(self, needs_helper, name=None):
        if not self._killed:
            assert not self._killed
            if name is None:
                name = needs_helper.__name__
            self.name = name
            new_helper = TaskHelper(name=name)
            self.child_helpers.append(new_helper)
            await needs_helper(new_helper)
            if self.killed:
                raise KilledError

    def kill(self, prefix=''):
        self._killed = True
        for helper in self.child_helpers:
            helper.kill(prefix+'--')

    def finish(self):
        for helper in self.child_helpers:
            helper.kill()

    @property
    def killed(self):
        return self._killed


def killable(coroutine):
    def needs_helper(*args, **kwargs):
        @cocotb.coroutine
        @wraps(coroutine)
        async def wrapper(helper):
            try:
                await coroutine(helper, *args, **kwargs)
                helper.finish()
            except KilledError:
                pass
        return wrapper
    return needs_helper
