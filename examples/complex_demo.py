import os

from slvcodec import filetestbench_generator


thisdir = os.path.dirname(__file__)


def make_slvcodec_package():
    complex_pkg_fn = os.path.join(thisdir, 'complex_pkg.vhd')
    directory = os.path.join(thisdir, 'generated')
    os.mkdir(directory)
    slvcodec_files = filetestbench_generator.add_slvcodec_files(directory, [complex_pkg_fn])
    return slvcodec_files


def make_complex_mag2_testbench():
    base_filenames = [
        os.path.join(thisdir, 'complex_pkg.vhd'),
        os.path.join(thisdir, 'complex_mag2.vhd'),
        ]
    slvcodec_fns = make_slvcodec_package()
    with_slvcodec_fns = base_filenames + slvcodec_fns
    directory = os.path.join(thisdir, 'generated')
    generated_fns, generated_wrapper_fns, resolved = filetestbench_generator.prepare_files(
        directory=directory, filenames=with_slvcodec_fns,
        top_entity='complex_mag2')
    return generated_fns

if __name__ == '__main__':
    # make_slvcodec_package()
    make_complex_mag2_testbench()
