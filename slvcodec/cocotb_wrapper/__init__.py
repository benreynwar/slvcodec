"""
This module wraps a small subset of cocotb.

This is useful because:
1) Sometimes we want to use coroutines in cocotb tests but
   also use these same coroutines elsewhere.
   If we use @cocot_wrapper.coroutine to wrap them then they
   work with cocotb but also with a standard asyncio event loop.
   e.g. I have higher level asynchronous libraries that I use to communicate
        with AXI4Lite designs on the FPGA and also use to communicate with
        a cocotb simulation.
2) The wrapper allows us to run the same tests outside cocotb using
   named pipes for communication with the simulator.

"""

import asyncio
import os

import cocotb
from cocotb import triggers as cocotb_triggers

from slvcodec import event


def using_cocotb():
    return 'COCOTB_SIM' in os.environ

def using_pipe():
    return 'PIPE_SIM' in os.environ


def terminate():
    if using_cocotb():
        pass
    else:
        raise event.TerminateException()


def coroutine(func):
    if using_cocotb():
        wrapped = cocotb.coroutine(func)
        return wrapped
    else:
        return func


def test():
    if using_cocotb():
        wrapped = cocotb.test()
        return wrapped
    else:
        def wrapped(func):
            return func
        return wrapped


def fork(coro):
    if using_cocotb():
        task = cocotb.fork(coro)
    elif using_pipe():
        task = event.LOOP.create_task(coro)
    else:
        task = asyncio.create_task(coro)
    return task


class AsyncioEvent:

    def __init__(self, loop):
        self.future = asyncio.Future(loop=loop)
        self.data = None

    def set(self, value):
        self.future.set_result(value)
        self.data = value

    def wait(self):
        return self.future
