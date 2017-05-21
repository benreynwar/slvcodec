import os

from vunit import VUnit

from slvcodec import filetestbench_generator

# Create VUnit instance by parsing command line arguments
vu = VUnit.from_argv()

# Create library 'lib'
lib = vu.add_library("lib")


package_files = (
    'vhdl_type_pkg.vhd',
    )
entity_file = 'dummy.vhd'
directory = 'deleteme'
os.makedirs(directory)
generated_fns = filetestbench_generator.prepare_files(directory, entity_file, package_files)

# Add all files ending in .vhd in current working directory to library
lib.add_source_files(generated_fns)
lib.add_source_files('../vhdl/*.vhd')
lib.add_source_files('*.vhd')

# Run vunit function
vu.main()
