import logging
import os

from slvcodec import entity, package, typs, config, symbolic_math

vhdl_dir = os.path.join(os.path.dirname(__file__),  'vhdl')


def test_dummy_width():
    # Parse and process entity
    entity_filename = os.path.join(vhdl_dir, 'dummy.vhd')
    parsed_entity = package.parsed_from_filename(entity_filename)
    processed_entity = entity.process_parsed_entity(parsed_entity)
    # Parse and process packages
    package_filenames = [os.path.join(vhdl_dir, 'vhdl_type_pkg.vhd')]
    packages = package.parse_process_and_resolve_packages(package_filenames)
    # Resolve the entity with the constants and types defined in the package.
    resolved_entity = processed_entity.resolve(packages=packages)
    # And get the ports from the resolved entity.
    o_data = resolved_entity.ports['o_data']
    i_dummy = resolved_entity.ports['i_dummy']
    # i_dummy width can be resolved without generics
    assert(i_dummy.typ.width.value() == 23)
    # o_data depends on the generic parameter size.
    length = 2
    w = typs.make_substitute_generics_function({'length': length})(
        o_data.typ.width)
    assert(w.value() == length * 6)


def test_module_instantiation():
    # Parse and process entity
    entity_filename = os.path.join(vhdl_dir, 'super_dummy.vhd')
    parsed_entity = package.parsed_from_filename(entity_filename)
    processed_entity = entity.process_parsed_entity(parsed_entity)
    subentity_filename = os.path.join(vhdl_dir, 'dummy.vhd')
    parsed_subentity = package.parsed_from_filename(subentity_filename)
    processed_subentity = entity.process_parsed_entity(parsed_subentity)
    # Parse and process packages
    package_filenames = [os.path.join(vhdl_dir, 'vhdl_type_pkg.vhd')]
    packages = package.parse_process_and_resolve_packages(package_filenames)
    # Resolve the entity with the constants and types defined in the package.
    resolved_subentity = processed_subentity.resolve(packages=packages, entities={})
    resolved_entity = processed_entity.resolve(
        packages=packages,
        entities={
            resolved_subentity.identifier: resolved_subentity,
            },
        )
    len(resolved_entity.components) == 2
    length_generics = {symbolic_math.str_expression(component.generics['length'])
                       for component in resolved_entity.components}
    assert(length_generics == {'2', 'length - 2'})


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_dummy_width()
    test_module_instantiation()
