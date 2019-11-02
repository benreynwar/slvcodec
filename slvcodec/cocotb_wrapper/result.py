import asyncio

from slvcodec import cocotb_wrapper, event
from cocotb import result as cocotb_result


class DummyTestSuccess:
    pass


if cocotb_wrapper.using_cocotb():
    TestSuccess = cocotb_result.TestSuccess
elif cocotb_wrapper.using_pipe():
    TestSuccess = event.TerminateException
else:
    TestSuccess = DummyTestSuccess


