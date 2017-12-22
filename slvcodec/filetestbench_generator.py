import logging
import os

import jinja2

from slvcodec import entity, package, typs, package_generator, config, vhdl_parser

logger = logging.getLogger(__name__)


def make_filetestbench(enty):
    '''
    Generate a testbench that reads inputs from a file, and writes outputs to
    a file.
    Args:
      `enty`: A resolved entity object parsed from the VHDL.
    '''
    # Generate a record type for the entity inputs (excluding clock).
    inputs = [p for p in enty.ports.values()
              if p.direction == 'in' and p.name not in entity.CLOCK_NAMES]
    input_names_and_types = [(p.name, p.typ) for p in inputs]
    input_record = typs.Record('t_input', input_names_and_types)
    # Generate a record type for the entity outputs.
    outputs = [p for p in enty.ports.values() if p.direction == 'out']
    output_names_and_types = [(p.name, p.typ) for p in outputs]
    output_record = typs.Record('t_output', output_names_and_types)
    # Generate declarations and definitions for the functions to convert
    # the input and output types to and from std_logic_vector.
    input_slv_declarations, input_slv_definitions = (
        package_generator.make_record_declarations_and_definitions(
            input_record))
    output_slv_declarations, output_slv_definitions = (
        package_generator.make_record_declarations_and_definitions(
            output_record))
    # Generate use clauses required by the testbench.
    use_clauses = '\n'.join([
        'use {}.{}.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values()])
    use_clauses += '\n' + '\n'.join([
        'use {}.{}_slvcodec.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values() if u.library not in ('ieee', 'std') and '_slvcodec' not in u.design_unit])
    # Get the list of generic parameters for the testbench.
    generic_params = '\n'.join(['{}: {};'.format(g.name, g.typ)
                                for g in enty.generics.values()])
    # Combine the input and output record definitions with the slv conversion
    # functions.
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
    # Read in the testbench template and format it.
    template_fn = os.path.join(os.path.dirname(__file__), 'templates',
                               'file_testbench.vhd')
    with open(template_fn, 'r') as f:
        filetestbench_template = jinja2.Template(f.read())
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
    '''
    Parses VHDL files, and generates a testbench for `top_entity`.
    Returns a tuple of a list of testbench files, and a dictionary
    of parsed objects.
    '''
    entities, packages = vhdl_parser.parse_and_resolve_files(filenames)
    resolved_entity = entities[top_entity]
    new_fns = [
        os.path.join(config.vhdldir, 'read_file.vhd'),
        os.path.join(config.vhdldir, 'write_file.vhd'),
        os.path.join(config.vhdldir, 'clock.vhd'),
    ]
    # Make file testbench
    ftb = make_filetestbench(resolved_entity)
    ftb_fn = os.path.join(directory, '{}_tb.vhd'.format(
        resolved_entity.identifier))
    with open(ftb_fn, 'w') as f:
        f.write(ftb)
    new_fns.append(ftb_fn)
    resolved = {
        'entities': entities,
        'packages': packages,
        }
    return new_fns, resolved


def add_slvcodec_files(directory, filenames):
    '''
    Parses files, and generates helper packages for existing packages that
    contain functions to convert types to and from std_logic_vector.
    '''
    parsed_packages = []
    filename_to_package_name = {}
    for filename in filenames:
        new_parsed_entities, new_parsed_packages = vhdl_parser.parse_file(filename)
        parsed_packages += new_parsed_packages
        if new_parsed_packages:
            assert len(new_parsed_packages) == 1
            filename_to_package_name[filename] = new_parsed_packages[0].identifier
    entities, packages = vhdl_parser.resolve_entities_and_packages(
        entities=[], packages=parsed_packages)
    combined_filenames = [os.path.join(config.vhdldir, 'txt_util.vhd'),
                          os.path.join(config.vhdldir, 'slvcodec.vhd')]
    for fn in filenames:
        if fn not in combined_filenames:
            combined_filenames.append(fn)
        if (fn in filename_to_package_name) and (fn[-len('slvcodec.vhd'):] != 'slvcodec.vhd'):
            package_name = filename_to_package_name[fn]
            slvcodec_pkg = package_generator.make_slvcodec_package(packages[package_name])
            slvcodec_package_filename = os.path.join(
                directory, '{}_slvcodec.vhd'.format(package_name))
            with open(slvcodec_package_filename, 'w') as f:
                f.write(slvcodec_pkg)
            combined_filenames.append(slvcodec_package_filename)
    return combined_filenames
