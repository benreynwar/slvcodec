import os
import random
import shutil
import logging
from collections import namedtuple

from slvcodec import test_utils, config

this_dir = os.path.abspath(os.path.dirname(__file__))
testoutput_dir = os.path.join(this_dir, '..', 'test_outputs')
coresdir = os.path.join(this_dir, 'cores')
vhdl_dir = os.path.join(this_dir, 'vhdl')


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
                'logic': 0,
                'slv': 1,
                },
            'i_datas': [0, 1, 2],
            } for i in range(20)]
        return data

    def check_output_data(self, input_data, output_data):
        o_data = [d['o_data'] for d in output_data]
        expected_data = [[0]*self.length] * len(o_data)
        assert o_data == expected_data
        o_firstdata = [d['o_firstdata'] for d in output_data]
        expected_firstdata = [d['i_datas'][0] for d in input_data]
        assert o_firstdata == expected_firstdata
        o_firstdatabit = [d['o_firstdatabit'] for d in output_data]
        expected_firstdatabit = [fd % 2 for fd in expected_firstdata]
        assert o_firstdatabit == expected_firstdatabit


def test_vunit_simple_integration():
    thistestoutput_dir = os.path.join(testoutput_dir, 'integration')
    if os.path.exists(thistestoutput_dir):
        shutil.rmtree(thistestoutput_dir)
    os.makedirs(thistestoutput_dir)
    entity_filename = os.path.join(vhdl_dir, 'dummy.vhd')
    package_filenames = [os.path.join(vhdl_dir, 'vhdl_type_pkg.vhd'),
                         os.path.join(vhdl_dir, 'test_pkg.vhd'),
                        ]
    filenames = [entity_filename] + package_filenames
    generation_directory = os.path.join(thistestoutput_dir, 'generated')
    os.makedirs(generation_directory)
    vu = config.setup_vunit(argv=[])
    test_utils.register_test_with_vunit(
        vu=vu,
        directory=generation_directory,
        filenames=filenames,
        top_entity='dummy',
        all_generics=[{'length': 4}, {'length': 31}],
        top_params={},
        test_class=DummyChecker,
        )
    all_ok = vu._main()
    assert all_ok


def test_vunit_coretest_integration():
    thistestoutput_dir = os.path.join(testoutput_dir, 'coretest_integration')
    if os.path.exists(thistestoutput_dir):
        shutil.rmtree(thistestoutput_dir)
    os.makedirs(thistestoutput_dir)
    coretest = {
        'core_name': 'Dummy',
        'entity_name': 'dummy',
        'all_generics': [{'length': 4}, {'length': 12}],
        'generator': DummyChecker,
        }
    config.setup_fusesoc(cores_roots=[coresdir])
    vu = config.setup_vunit(argv=[])
    test_utils.register_coretest_with_vunit(vu, coretest, thistestoutput_dir)
    all_ok = vu._main()
    assert all_ok

if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_vunit_simple_integration()
    test_vunit_coretest_integration()
