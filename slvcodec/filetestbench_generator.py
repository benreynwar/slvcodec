import logging
import os

import jinja2

from slvcodec import entity, package, typs, package_generator

logger = logging.getLogger(__name__)


def make_filetestbench(enty):
    # Make records for inputs and outputs.
    inputs = [p for p in enty.ports.values()
              if p.direction == 'in' and p.name not in entity.CLOCK_NAMES]
    outputs = [p for p in enty.ports.values() if p.direction == 'out']
    input_names_and_types = [(p.name, p.typ) for p in inputs]
    output_names_and_types = [(p.name, p.typ) for p in outputs]
    input_record = typs.Record(
        't_input'.format(enty.identifier), input_names_and_types)
    output_record = typs.Record(
        't_output'.format(enty.identifier), output_names_and_types)
    input_slv_declarations, input_slv_definitions = package_generator.make_record_declarations_and_definitions(
        input_record)
    output_slv_declarations, output_slv_definitions = package_generator.make_record_declarations_and_definitions(
        output_record)
    template_fn = os.path.join(os.path.dirname(__file__), 'templates', 'file_testbench.vhd')
    with open(template_fn, 'r') as f:
        filetestbench_template = jinja2.Template(f.read())
    use_clauses = '\n'.join([
        'use {}.{}.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values()])
    use_clauses += '\n' + '\n'.join([
        'use {}.{}_slvcodec.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values() if u.library != 'ieee'])
    generic_params = '\n'.join(['{}: {};'.format(g.name, g.typ)
                                for g in enty.generics.values()])
    definitions = '\n'.join([
        input_record.declaration(), output_record.declaration(),
        input_slv_declarations, input_slv_definitions,
        output_slv_declarations, output_slv_definitions])
    clk_names = [p.name for p in enty.ports.values()
                 if (p.direction == 'in') and (p.name in entity.CLOCK_NAMES)]
    clk_connections = '\n'.join(['{} => {},'.format(clk, clk) for clk in clk_names])
    connections = ',\n'.join(['{} => {}.{}'.format(
        p.name, {'in': 'input_data', 'out': 'output_data'}[p.direction], p.name)
                              for p in enty.ports.values() if p.name not in clk_names])
    dut_generics = ',\n'.join(['{} => {}'.format(g.name, g.name)
                               for g in enty.generics.values()])
    filetestbench = filetestbench_template.render(
        test_name='{}_tb'.format(enty.identifier),
        use_clauses=use_clauses,
        generic_params=generic_params,
        definitions=definitions,
        dut_generics=dut_generics,
        dut_name=enty.identifier,
        clk_connections=clk_connections,
        connections=connections,
        )
    return filetestbench


def prepare_files(directory, filenames, top_entity):
    entities, packages = entity.process_files(filenames)
    resolved_entity = entities[top_entity]
    new_fns = []
    # Make file testbench
    ftb = make_filetestbench(resolved_entity)
    ftb_fn = os.path.join(directory, '{}_tb.vhd'.format(
        resolved_entity.identifier))
    with open(ftb_fn, 'w') as f:
        f.write(ftb)
    new_fns.append(ftb_fn)
    # Make slvcodec packages
    for pkg in packages.values():
        if pkg.identifier not in package.standard_packages:
            slvcodec_pkg = package_generator.make_slvcodec_package(pkg)
            slvcodec_package_filename = os.path.join(
                directory, '{}_slvcodec.vhd'.format(pkg.identifier))
            with open(slvcodec_package_filename, 'w') as f:
                f.write(slvcodec_pkg)
            new_fns.append(slvcodec_package_filename)
    return new_fns, resolved_entity


if __name__ == '__main__':
    filenames = (
        'tests/vhdl_type_pkg.vhd',
        'tests/dummy.vhd',
        )
    top_entity = 'dummy'
    directory = 'deleteme'
    os.makedirs(directory)
    prepare_files(directory, filenames, top_entity)
