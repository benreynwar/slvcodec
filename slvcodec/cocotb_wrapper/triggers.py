"""
A wrapper around a subset of the cocotb.triggers module.
"""

import asyncio

from cocotb import triggers as cocotb_triggers

from slvcodec import cocotb_wrapper, event


def Combine(*awaitables):
    if cocotb_wrapper.using_cocotb():
        return cocotb_triggers.Combine(*awaitables)
    elif cocotb_wrapper.using_pipe():
        return event.gather(*awaitables)
    else:
        return asyncio.gather(*awaitables)


def Event():
    if cocotb_wrapper.using_cocotb():
        return cocotb_triggers.Event()
    elif cocotb_wrapper.using_pipe():
        return cocotb_wrapper.AsyncioEvent(event.LOOP)
    else:
        return cocotb_wrapper.AsyncioEvent(asyncio.get_event_loop())


def Timer(*args, **kwargs):
    assert cocotb_wrapper.using_cocotb()
    return cocotb_triggers.Timer(*args, **kwargs)


def RisingEdge(signal):
    if cocotb_wrapper.using_cocotb():
        return cocotb_triggers.RisingEdge(signal)
    else:
        return event.RisingEdge(signal)


def ReadOnly():
    if cocotb_wrapper.using_cocotb():
        return cocotb_triggers.ReadOnly()
    else:
        return event.ReadOnly()
