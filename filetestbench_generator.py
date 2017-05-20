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
        't_{}_inputs'.format(entity.identifier), input_names_and_types)
    output_record = typs.Record(
        't_{}_inputs'.format(entity.identifier), output_names_and_types)
    input_slv_declarations, input_slv_definitions = package_generator.make_record_declarations_and_definitions(
        input_record)
    output_slv_declarations, output_slv_definitions = package_generator.make_record_declarations_and_definitions(
        output_record)
    body = [input_record.declaration(), output_record.declaration(),
            input_slv_definitions, output_slv_definitions]
    template_fn = os.path.join(os.path.dirname(__file__), 'templates', 'file_testbench.vhd')
    with open(template_fn, 'r') as f:
        filetestbench_template = jinja2.Template(f.read())
    use_clauses = '\n'.join([
        'use {}.{}.{};'.format(u.library, u.design_unit, u.name_within)
        for u in entity.uses.values()])
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
        use_clauses=use_clauses,
        generic_params=generic_params,
        definitions=definitions,
        dut_generics=dut_generics,
        connections=connections,
        )
    return filetestbench


if __name__ == '__main__':
    package_files = (
        'tests/vhdl_type_pkg.vhd',
        )
    entity_file = 'tests/dummy.vhdl'
    parsed_entity = entity.parsed_entity_from_filename('tests/dummy.vhd')
    entity = entity.process_parsed_entity(parsed_entity)
    packages = package.process_packages(['tests/vhdl_type_pkg.vhd'])
    resolved_entity = entity.resolve(packages=packages)
    make_filetestbench(resolved_entity)
