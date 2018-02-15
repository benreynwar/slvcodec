import logging
import os
import random
import shutil

from slvcodec import filetestbench_generator
from slvcodec import entity, package, typs, config, vhdl_parser

vhdl_dir = os.path.join(os.path.dirname(__file__),  'vhdl')

testoutput_dir = os.path.join(os.path.dirname(__file__), 'test_output')


def test_dummy_width():
    # Parse and process entity
    entity_filename = os.path.join(vhdl_dir, 'dummy.vhd')
    package_filenames = [os.path.join(vhdl_dir, 'vhdl_type_pkg.vhd')]
    entities, packages = vhdl_parser.parse_and_resolve_files([entity_filename] + package_filenames)
    # Resolve the entity with the constants and types defined in the package.
    resolved_entity = entities['dummy']
    # And get the ports from the resolved entity.
    o_data = resolved_entity.ports['o_data']
    i_dummy = resolved_entity.ports['i_dummy']
    # i_dummy width can be resolved without generics
    assert i_dummy.typ.width.value() == 23
    # o_data depends on the generic parameter size.
    length = 2
    w = typs.make_substitute_generics_function({'length': length})(
        o_data.typ.width)
    assert w.value() == length * 6


def test_conversion():
    output_dir = os.path.join(testoutput_dir, 'test_conversion')
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
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
    entity_filename = os.path.join(vhdl_dir, 'dummy.vhd')
    package_filenames = [os.path.join(vhdl_dir, 'vhdl_type_pkg.vhd'),
                         os.path.join(vhdl_dir, 'test_pkg.vhd')]
    filenames = [entity_filename] + package_filenames

    generation_directory = os.path.join(output_dir, 'generated')
    os.makedirs(generation_directory)

    with_slvcodec_files = filetestbench_generator.add_slvcodec_files(
        generation_directory, filenames)
    ftb_directory = os.path.join(generation_directory, 'ftb')
    top_entity = 'dummy'
    os.mkdir(ftb_directory)
    generated_tb_fns, generated_dut_fns, resolved = filetestbench_generator.prepare_files(
        directory=ftb_directory, filenames=with_slvcodec_files,
        top_entity=top_entity)
    ent = resolved['entities'][top_entity]
    generics = {'length': 3}
    for d in data:
        slv = ent.inputs_to_slv(d, generics=generics)
        obj = ent.inputs_from_slv(slv, generics=generics)
        assert obj == d 


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    #test_conversion()
    test_dummy_width()
