import os
import shutil
import logging
import random

from slvcodec import test_utils, config
import test_integration

logger = logging.getLogger(__name__)


this_dir = os.path.abspath(os.path.dirname(__file__))
testoutput_dir = os.path.join(this_dir, '..', 'test_outputs')
vhdl_dir = os.path.join(this_dir, 'vhdl')


def dummy_checker_testbench(length):
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
        opt = yield ipt
        assert opt['o_data'] == [0] * length
        assert opt['o_firstdata'] == ipt['i_datas'][0]
        assert opt['o_firstdatabit'] == ipt['i_datas'][0] % 2


def test_simple_integration():
    directory = os.path.join(testoutput_dir, 'pipe_integration')
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
    test_generator = dummy_checker_testbench(generics['length'])
    test_utils.run_pipe_test(directory, filenames, top_entity, generics, test_generator)


def make_dummy_checker_testgenerator(length):
    def dummy_checker_testgenerator(dut):
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
            dut.set_inputs(ipt)
            logger.debug('Yielding in the generator')
            yield test_utils.TriggerOnCycle(dut)
            opt = dut.get_outputs()
            assert opt['o_data'] == [0] * length
            assert opt['o_firstdata'] == ipt['i_datas'][0]
            assert opt['o_firstdatabit'] == ipt['i_datas'][0] % 2
        logger.debug('Finished generator')
    return dummy_checker_testgenerator

def test_simple_integration2():
    directory = os.path.join(testoutput_dir, 'pipe_integration2')
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
    test_generator = make_dummy_checker_testgenerator(generics['length'])
    test_utils.run_pipe_test2(directory, filenames, top_entity, generics, [test_generator])

if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_simple_integration2()
