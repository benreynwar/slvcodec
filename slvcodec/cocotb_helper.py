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

    @property
    def _finished(self):
        return self.task._finished

    @property
    def _outcome(self):
        return self.task._outcome


class KillableEvent:

    def __init__(self, on_finish):
        self.event = triggers.Event()
        self._killed = False
        self.on_finish = on_finish

    def kill(self):
        self._killed = True

    async def wait(self):
        val = await self.event.wait()
        if self.killed:
            raise KilledError
        self.on_finish(self)
        return val

    def set(self, value):
        self.event.set(value)
        self.data = value

    @property
    def killed(self):
        return self._killed


class TaskHelper:

    def __init__(self, name=None):
        self.child_helpers = []
        self.events = set()
        self._killed = False
        self.name = name

    def remove_event(self, event):
        self.events.remove(event)

    def Event(self):
        event = KillableEvent(on_finish=self.remove_event)
        self.events.add(event)
        return event

    def Join(self, task):
        return triggers.Join(task.task)

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
            raise KilledError

    @cocotb.coroutine
    async def add(self, needs_helper, name=None):
        if not self._killed:
            assert not self._killed
            if name is None:
                name = needs_helper.__name__
            self.name = name
            new_helper = TaskHelper(name=name)
            self.child_helpers.append(new_helper)
            value = await needs_helper(new_helper)
            if self.killed:
                raise KilledError
            return value
        else:
            raise KilledError

    def kill(self, prefix=''):
        self._killed = True
        for helper in self.child_helpers:
            helper.kill(prefix+'--')
        for event in self.events:
            event.kill()

    def finish(self):
        for helper in self.child_helpers:
            helper.kill()
        for event in self.events:
            event.kill()

    @property
    def killed(self):
        return self._killed


def killable(coroutine):
    def needs_helper(*args, **kwargs):
        @cocotb.coroutine
        @wraps(coroutine)
        async def wrapper(helper):
            try:
                return await coroutine(helper, *args, **kwargs)
                helper.finish()
            except KilledError:
                pass
        return wrapper
    return needs_helper
