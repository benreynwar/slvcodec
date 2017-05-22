import random
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
generated_fns, entity = filetestbench_generator.prepare_files(directory, entity_file, package_files)

# Add all files ending in .vhd in current working directory to library
lib.add_source_files(generated_fns)
lib.add_source_files('../vhdl/*.vhd')
lib.add_source_files('*.vhd')

datainfilename = os.path.join(directory, 'indata.das')
dataoutfilename = os.path.join(directory, 'outdata.das')

data = [{
    'reset': random.randint(0, 1),
    'i_valid': random.randint(0, 1),
    'i_dummy': {
        'manydata': [0, 0],
        'data': 0,
        'logic': 0,
        'slv': 1,
        },
    } for i in range(20)]

for line in data:
    slv = entity.inputs_to_slv(line)
lines = [entity.inputs_to_slv(line) for line in data]
with open(datainfilename, 'w') as f:
    f.write('\n'.join(lines))

tb_generated = lib.entity('dummy_tb')
tb_generated.add_config(name="bug", generics={
    'datainfilename': datainfilename,
    'dataoutfilename': dataoutfilename,
    'length': 5,
    })
# Run vunit function
vu.main()
