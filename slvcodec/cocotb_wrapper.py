import asyncio
import os

import pytest
cocotb = pytest.importorskip('cocotb')
from cocotb import triggers

from slvcodec import event


def using_cocotb():
    return 'COCOTB_SIM' in os.environ


def terminate():
    if using_cocotb():
        pass
    else:
        raise event.TerminateException()


def Combine(*awaitables):
    if using_cocotb():
        return triggers.Combine(*awaitables)
    else:
        return event.gather(*awaitables)


def Event():
    if using_cocotb():
        return triggers.Event()
    else:
        return AsyncioEvent()


def coroutine(func):
    if using_cocotb():
        wrapped = cocotb.coroutine(func)
        return wrapped
    else:
        return func



class AsyncioEvent:

    def __init__(self):
        self.future = asyncio.Future()

    def set(self, value):
        self.future.set_result(value)

    def wait(self):
        return self.future


class CocotbFuture:

    def __init__(self):
        self.event = triggers.Event()
        self.is_done = False
        self.value = None

    def result(self):
        if self.is_done:
            return self.value
        else:
            raise Exception("Not done")

    def set_result(self, value):
        self.is_done = True
        self.value = value
        self.event.set(value)

    def set_exception(self, exception):
        raise NotImplementedError()

    def done(self):
        return self.is_done

    def cancelled(self):
        return False

    def add_done_callback(self):
        raise NotImplementedError()

    def remove_done_callback(self):
        raise NotImplementedError()

    def cancel(self):
        raise NotImplementedError()

    def exception(self):
        raise NotImplementedError()

    def get_loop(self):
        raise NotImplementedError()

    def __await__(self):
        yield self.event.wait()
