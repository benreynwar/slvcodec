import logging
import os

from slvcodec import package, config

vhdl_dir = os.path.join(os.path.dirname(__file__),  'vhdl')


def test_dummy_width():
    package_filenames = [os.path.join(vhdl_dir, 'vhdl_type_pkg.vhd')]
    packages = package.parse_process_and_resolve_packages(package_filenames)
    p = packages['vhdl_type_pkg']
    t = p.types['t_dummy']
    assert(t.width.value() == 23)


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_dummy_width()
