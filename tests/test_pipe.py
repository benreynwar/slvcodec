import os
import shutil
import logging

from slvcodec import test_utils, config
import test_integration


this_dir = os.path.abspath(os.path.dirname(__file__))
testoutput_dir = os.path.join(this_dir, '..', 'test_outputs')
vhdl_dir = os.path.join(this_dir, 'vhdl')


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
    test_generator = test_integration.DummyChecker
    test_utils.run_pipe_test(directory, filenames, top_entity, generics, test_generator)


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_simple_integration()
