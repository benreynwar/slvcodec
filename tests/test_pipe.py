import os
import shutil
import logging
import random
import json

from slvcodec import test_utils, config, event, cocotb_dut
import slvcodec.cocotb_wrapper as cocotb
from slvcodec.cocotb_wrapper import triggers, result
import test_integration

logger = logging.getLogger(__name__)


this_dir = os.path.abspath(os.path.dirname(__file__))
testoutput_dir = os.path.join(this_dir, '..', 'test_outputs')
vhdl_dir = os.path.join(this_dir, 'vhdl')


@cocotb.coroutine
async def dummy_checker(dut, generics):
    length = generics['length']
    n_data = 20
    max_data = pow(2, 6)-1
    for i in range(n_data):
        await triggers.RisingEdge(dut.clk)
        dut.reset <= random.randint(0, 1)
        dut.i_valid <= random.randint(0, 1)
        if not hasattr(dut, 'i_dummy'):
            import pdb
            pdb.set_trace()
        dut.i_dummy <= {
            'manydata': [random.randint(0, max_data) for i in range(2)],
            'data': random.randint(0, max_data),
            'logic': random.randint(0, 1),
            'slv': 7,
            }
        dut.i_datas <= [random.randint(0, max_data) for i in range(3)]
        await triggers.ReadOnly()
        assert dut.o_data == [0] * length
        assert dut.o_firstdata == int(dut.i_datas[0])
        logger.debug('expected is {} and received is {}'.format(dut.i_datas[0], dut.o_firstdata))
        assert dut.o_firstdatabit == int(dut.i_datas[0]) % 2
    logger.debug('Finished generator')
    raise result.TestSuccess()


@cocotb.test()
async def cocotb_coro(dut):
    params_filename = os.environ['test_params_filename']
    with open(params_filename) as f:
        params = json.load(f)
    generics = params['generics']
    mapping = params['mapping']
    cocotb_dut.apply_mapping(dut, mapping, separator='_')
    cocotb.fork(test_utils.clock(dut.clk, 2))
    await dummy_checker(dut, generics)


def test_dummy():

    entity_filename = os.path.join(vhdl_dir, 'dummy.vhd')
    package_filenames = [
        os.path.join(vhdl_dir, 'vhdl_type_pkg.vhd'),
        os.path.join(vhdl_dir, 'test_pkg.vhd'),
    ]
    filenames = package_filenames + [entity_filename]
    top_entity = 'dummy'
    generics = {'length': 2}

    @cocotb.coroutine
    async def pipe_coro(dut):
        await dummy_checker(dut, generics)

    pipe_directory = os.path.join(testoutput_dir, 'pipe_integration')
    if os.path.exists(pipe_directory):
        shutil.rmtree(pipe_directory)
    os.makedirs(pipe_directory)
    test_utils.run_pipe_test(pipe_directory, filenames, top_entity, generics, pipe_coro, needs_resolved=False)
    cocotb_directory = os.path.join(testoutput_dir, 'cocotb_integration')
    if os.path.exists(cocotb_directory):
        shutil.rmtree(cocotb_directory)
    os.makedirs(cocotb_directory)

    test_utils.run_with_cocotb(cocotb_directory, filenames, top_entity, generics, 'test_pipe')


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_dummy()
