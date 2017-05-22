import logging
import os

import jinja2

from slvcodec import entity, package, typs, package_generator

logger = logging.getLogger(__name__)


def make_filetestbench(entity):
    # Make records for inputs and outputs.
    inputs = [p for p in entity.ports.values() if p.direction == 'in']
    outputs = [p for p in entity.ports.values() if p.direction == 'out']
    input_names_and_types = [(p.name, p.typ) for p in inputs]
    output_names_and_types = [(p.name, p.typ) for p in outputs]
    input_record = typs.Record(
        't_input'.format(entity.identifier), input_names_and_types)
    output_record = typs.Record(
        't_output'.format(entity.identifier), output_names_and_types)
    input_slv_declarations, input_slv_definitions = package_generator.make_record_declarations_and_definitions(
        input_record)
    output_slv_declarations, output_slv_definitions = package_generator.make_record_declarations_and_definitions(
        output_record)
    template_fn = os.path.join(os.path.dirname(__file__), 'templates', 'file_testbench.vhd')
    with open(template_fn, 'r') as f:
        filetestbench_template = jinja2.Template(f.read())
    use_clauses = '\n'.join([
        'use {}.{}.{};'.format(u.library, u.design_unit, u.name_within)
        for u in entity.uses.values()])
    use_clauses += '\n' + '\n'.join([
        'use {}.{}_slvcodec.{};'.format(u.library, u.design_unit, u.name_within)
        for u in entity.uses.values() if u.library != 'ieee'])
    generic_params = '\n'.join(['{}: {};'.format(g.name, g.typ)
                                for g in entity.generics.values()])
    definitions = '\n'.join([
        input_record.declaration(), output_record.declaration(),
        input_slv_declarations, input_slv_definitions,
        output_slv_declarations, output_slv_definitions])
    connections = ',\n'.join(['{} => {}.{}'.format(
        p.name, {'in': 'input_data', 'out': 'output_data'}[p.direction], p.name)
                              for p in entity.ports.values() if p.name != 'clk'])
    dut_generics = ',\n'.join(['{} => {}'.format(g.name, g.name)
                               for g in entity.generics.values()])
    filetestbench = filetestbench_template.render(
        test_name='{}_tb'.format(entity.identifier),
        use_clauses=use_clauses,
        generic_params=generic_params,
        definitions=definitions,
        dut_generics=dut_generics,
        dut_name=entity.identifier,
        connections=connections,
        )
    return filetestbench


def prepare_files(directory, entity_file, package_files):
    parsed_entity = entity.parsed_entity_from_filename(entity_file)
    unresolved_entity = entity.process_parsed_entity(parsed_entity)
    packages = package.process_packages(package_files)
    resolved_entity = unresolved_entity.resolve(packages=packages)
    new_fns = []
    # Make file testbench
    ftb = make_filetestbench(resolved_entity)
    ftb_fn = os.path.join(directory, '{}_tb.vhd'.format(
        resolved_entity.identifier))
    with open(ftb_fn, 'w') as f:
        f.write(ftb)
    new_fns.append(ftb_fn)
    # Make slvcodec packages
    for package_file in package_files:
        parsed_package = package.parsed_package_from_filename(package_file)
        pkg = packages[parsed_package.packages[0].identifier]
        slvcodec_pkg = package_generator.make_slvcodec_package(pkg)
        base_name = package_generator.get_base_name(package_file)
        slvcodec_package_filename = os.path.join(
            directory, base_name + '_slvcodec.vhd')
        with open(slvcodec_package_filename, 'w') as f:
            f.write(slvcodec_pkg)
        new_fns.append(slvcodec_package_filename)
    return new_fns, resolved_entity


if __name__ == '__main__':
    package_files = (
        'tests/vhdl_type_pkg.vhd',
        )
    entity_file = 'tests/dummy.vhd'
    directory = 'deleteme'
    os.makedirs(directory)
    prepare_files(directory, entity_file, package_files)
