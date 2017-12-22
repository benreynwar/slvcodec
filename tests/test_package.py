import logging
import os

from slvcodec import package, config, vhdl_parser

vhdl_dir = os.path.join(os.path.dirname(__file__),  'vhdl')


def test_dummy_width():
    package_filenames = [os.path.join(vhdl_dir, 'vhdl_type_pkg.vhd')]
    entities, packages = vhdl_parser.parse_and_resolve_files(package_filenames)
    p = packages['vhdl_type_pkg']
    t = p.types['t_dummy']
    assert t.width.value() == 23
    aau = p.types['array_of_array_of_unsigned']
    assert aau.width.value() == 6*6*4


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_dummy_width()
