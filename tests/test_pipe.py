import os
import shutil
import logging
import random

from slvcodec import test_utils, config, event
import test_integration

logger = logging.getLogger(__name__)


this_dir = os.path.abspath(os.path.dirname(__file__))
testoutput_dir = os.path.join(this_dir, '..', 'test_outputs')
vhdl_dir = os.path.join(this_dir, 'vhdl')


async def dummy_checker(dut, length):
    n_data = 20
    max_data = pow(2, 6)-1
    for i in range(n_data):
        ipt = {
            'reset': random.randint(0, 1),
            'i_valid': random.randint(0, 1),
            'i_dummy': {
                'manydata': [random.randint(0, max_data) for i in range(2)],
                'data': random.randint(0, max_data),
                'logic': random.randint(0, 1),
                'slv': 7,
                },
            'i_datas': [random.randint(0, max_data) for i in range(3)],
            }
        dut.set(ipt)
        await event.NextCycleFuture()
        opt = dut.get()
        assert opt['o_data'] == [0] * length
        assert opt['o_firstdata'] == ipt['i_datas'][0]
        logger.debug('expected is {} and received is {}'.format(ipt['i_datas'][0], opt['o_firstdata']))
        assert opt['o_firstdatabit'] == ipt['i_datas'][0] % 2
    logger.debug('Finished generator')
    raise event.TerminateException()


def test_simple_pipe():
    directory = os.path.join(testoutput_dir, 'pipe_integration3')
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory)

    entity_filename = os.path.join(vhdl_dir, 'dummy.vhd')
    package_filenames = [
        os.path.join(vhdl_dir, 'vhdl_type_pkg.vhd'),
        os.path.join(vhdl_dir, 'test_pkg.vhd'),
    ]
    filenames = package_filenames + [entity_filename]
    top_entity = 'dummy'
    generics = {'length': 2}

    simulator = event.Simulator(directory, filenames, top_entity, generics)
    loop = event.EventLoop(simulator)
    loop.create_task(dummy_checker(simulator.dut, generics['length']))
    loop.run_forever()

if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_simple_pipe()
