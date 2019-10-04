import os
import random
import shutil
import logging

import jinja2
import pytest

from slvcodec import test_utils, config

this_dir = os.path.abspath(os.path.dirname(__file__))
testoutput_dir = os.path.join(this_dir, '..', 'test_outputs')
coresdir = os.path.join(this_dir, 'cores')
vhdl_dir = os.path.join(this_dir, 'vhdl')

fusesoc_config_template = os.path.join(this_dir, 'fusesoc.conf.j2')
def get_fusesoc_config_filename():
    fusesoc_config_filename = os.path.join(this_dir, 'fusesoc.conf')
    if not os.path.exists(fusesoc_config_filename):
        with open(fusesoc_config_template, 'r') as f:
            template = jinja2.Template(f.read())
        content = template.render(this_dir=this_dir)
        with open(fusesoc_config_filename, 'w') as f:
            f.write(content)
    return fusesoc_config_filename


class DummyChecker:

    def __init__(self, resolved, generics, top_params):
        self.resolved = resolved
        self.generics = generics
        self.length = generics['length']

    def make_input_data(self):
        max_data = pow(2, 6)-1
        data = [{
            'reset': random.randint(0, 1),
            'i_valid': random.randint(0, 1),
            'i_dummy': {
                'manydata': [random.randint(0, max_data) for i in range(2)],
                'data': random.randint(0, max_data),
                'logic': random.randint(0, 1),
                'slv': 7,
            },
            'i_datas': [random.randint(0, max_data) for i in range(3)],
        } for i in range(20)]
        self.input_data = data
        return data

    def check_output_data(self, input_data, output_data):
        assert len(input_data) == len(output_data)
        assert self.input_data == input_data
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
    package_filenames = [
        os.path.join(vhdl_dir, 'vhdl_type_pkg.vhd'),
        os.path.join(vhdl_dir, 'test_pkg.vhd'),
    ]
    filenames = [entity_filename] + package_filenames
    generation_directory = os.path.join(thistestoutput_dir, 'generated')
    os.makedirs(generation_directory)
    vu = config.setup_vunit(argv=['--dont-catch-exceptions'])
    test_utils.register_test_with_vunit(
        vu=vu,
        directory=generation_directory,
        filenames=filenames,
        top_entity='dummy',
        all_generics=[{'length': 4}, {'length': 31}],
        top_params={},
        test_class=DummyChecker,
        )
    all_ok = vu._main(post_run=None)
    assert all_ok



def test_vunit_coretest_integration():
    fusesoc_generators = pytest.importorskip('fusesoc_generators')
    thistestoutput_dir = os.path.join(testoutput_dir, 'coretest_integration')
    if os.path.exists(thistestoutput_dir):
        shutil.rmtree(thistestoutput_dir)
    os.makedirs(thistestoutput_dir)
    coretest = {
        'core_name': 'Dummy',
        'entity_name': 'dummy',
        'param_sets': [{
            'top_params': {},
            'generic_sets': [{'length': 3}],
        }],
        'generator': DummyChecker,
        }
    vu = config.setup_vunit(argv=['--dont-catch-exceptions'])
    test_utils.register_coretest_with_vunit(
        vu, coretest, thistestoutput_dir,
        fusesoc_config_filename=get_fusesoc_config_filename())
    all_ok = vu._main(post_run=None)
    assert all_ok


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_vunit_simple_integration()
    test_vunit_coretest_integration()
