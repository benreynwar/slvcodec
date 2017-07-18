import os
import random
import shutil
import logging
from collections import namedtuple

from vunit.ui import VUnit
from vunit.simulator_factory import SimulatorFactory

from slvcodec import test_utils, config

testoutput_dir = os.path.join(os.path.dirname(__file__), '..', 'test_outputs')
vhdl_dir = os.path.join(os.path.dirname(__file__),  'vhdl')


class DummyChecker:

    def __init__(self, entity, generics, top_params):
        self.entity = entity
        self.generics = generics
        self.length = generics['length']

    def make_input_data(self):
        data = [{
            'reset': random.randint(0, 1),
            'i_valid': random.randint(0, 1),
            'i_dummy': {
                'manydata': [0, 0],
                'data': 0,
                'anint': 0,
                'anotherint': 0,
                'logic': 0,
                'slv': 1,
                },
            } for i in range(20)]
        return data

    def check_output_data(self, input_data, output_data):
        o_data = [d['o_data'] for d in output_data]
        expected_data = [[0]*self.length] * len(o_data)
        assert(o_data == expected_data)


SimulatorArgs = namedtuple(
    'SimulatorArgs', ['output_path', 'gui', 'gtkwave_fmt', 'gtkwave_args'])


def test_vunit_integration():
    thistestoutput_dir = os.path.join(testoutput_dir, 'integration')
    if os.path.exists(thistestoutput_dir):
        shutil.rmtree(thistestoutput_dir)
    os.makedirs(thistestoutput_dir)
    output_path = os.path.join(thistestoutput_dir, 'integration', 'vunit_out')
    sim_args = SimulatorArgs(
        output_path=output_path, gui=False, gtkwave_fmt=None, gtkwave_args='')
    vu = VUnit(output_path=output_path,
               simulator_factory=SimulatorFactory(sim_args),
               )
    entity_filename = os.path.join(vhdl_dir, 'dummy.vhd')
    package_filenames = [os.path.join(vhdl_dir, 'vhdl_type_pkg.vhd'),
                         os.path.join(vhdl_dir, 'test_pkg.vhd'),
                         ]
    filenames = [entity_filename] + package_filenames
    generation_directory = os.path.join(thistestoutput_dir, 'generated')
    os.makedirs(generation_directory)
    test_utils.update_vunit(
        vu=vu,
        directory=generation_directory,
        filenames=filenames,
        top_entity='dummy',
        all_generics=[{'length': 4}, {'length': 31}],
        top_params={},
        test_class=DummyChecker,
        )
    all_ok = vu._main()
    assert(all_ok)

if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_vunit_integration()
