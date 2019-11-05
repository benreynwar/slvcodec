import asyncio

from slvcodec import cocotb_wrapper, event
from cocotb import result as cocotb_result


class DummyTestSuccess:
    pass


if cocotb_wrapper.using_cocotb():
    TestSuccess = cocotb_result.TestSuccess
else:
    TestSuccess = event.TerminateException
