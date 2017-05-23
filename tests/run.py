import os

from vunit import VUnit

from dummy_tb import DummyTest
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
generics = {'length': 3}

test = DummyTest(entity, generics)
i_data = test.make_input_data()
lines = [entity.inputs_to_slv(line, generics=generics) for line in i_data]
with open(datainfilename, 'w') as f:
    f.write('\n'.join(lines))


def post_check(directory):
    with open(dataoutfilename, 'r') as f:
        lines = f.readlines()
    o_data = [entity.outputs_from_slv(line, generics=generics) for line in lines]
    test.check_output_data(i_data, o_data)
    return True

tb_generated = lib.entity('dummy_tb')
tb_generated.add_config(
    name="bug",
    generics={
        'datainfilename': datainfilename,
        'dataoutfilename': dataoutfilename,
        'length': 5,
    },
    post_check=post_check,
    )
# Run vunit function
vu.main()
