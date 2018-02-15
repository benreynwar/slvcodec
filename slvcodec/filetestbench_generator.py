import logging
import os

import jinja2

from slvcodec import entity, typs, package_generator, config, vhdl_parser

logger = logging.getLogger(__name__)


def make_double_wrapper(enty, default_generics=None):
    if default_generics is None:
        default_generics = {}
    # Get the list of generic parameters for the testbench.
    entity_generics = ';\n'.join(['{}: {}'.format(g.name, g.typ)
                                  for g in enty.generics.values()])
    entity_generics_with_defaults = []
    for g in enty.generics.values():
        as_str = '{}: {}'.format(g.name, g.typ)
        if g.name in default_generics:
            as_str += ' := {}'.format(default_generics[g.name])
        as_str += ';'
        entity_generics_with_defaults.append(as_str)
    entity_generics_with_defaults = '\n'.join(entity_generics_with_defaults)[:-1]
    wrapped_generics = ',\n'.join(['{} => {}'.format(g.name, g.name)
                                   for g in enty.generics.values()])
    # Generate use clauses required by the testbench.
    use_clauses = '\n'.join([
        'use {}.{}.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values()])
    use_clauses += '\n' + '\n'.join([
        'use {}.{}_slvcodec.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values()
        if u.library not in ('ieee', 'std') and '_slvcodec' not in u.design_unit])
    # Read in the toslvcodec template and format it.
    template_and_wrapped_names = (
        ('fromslvcodec.vhd', enty.identifier),
        ('toslvcodec.vhd', enty.identifier + '_fromslvcodec'),
        )
    wrappers = []
    for template_name, wrapped_name in template_and_wrapped_names:
        template_fn = os.path.join(os.path.dirname(__file__), 'templates', template_name)
        with open(template_fn, 'r') as f:
            template = jinja2.Template(f.read())
        wrappers.append(template.render(
            entity_name=enty.identifier,
            entity_generics=entity_generics,
            entity_generics_with_defaults=entity_generics_with_defaults,
            use_clauses=use_clauses,
            wrapped_generics=wrapped_generics,
            wrapped_name=wrapped_name,
            ports=list(enty.ports.values()),
            ))
    return wrappers


def make_filetestbench(enty, add_double_wrapper=False, use_vunit=True,
                       default_output_path=None, default_generics=None):
    '''
    Generate a testbench that reads inputs from a file, and writes outputs to
    a file.
    Args:
      `enty`: A resolved entity object parsed from the VHDL.
    '''
    if default_generics is None:
        default_generics = {}
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
        for u in enty.uses.values()
        if u.library not in ('ieee', 'std') and '_slvcodec' not in u.design_unit])
    # Get the list of generic parameters for the testbench.
    generic_params = []
    for g in enty.generics.values():
        as_str = '{}: {}'.format(g.name, g.typ)
        if g.name in default_generics:
            as_str += ' := {}'.format(default_generics[g.name])
        as_str += ';'
        generic_params.append(as_str)
    generic_params = '\n'.join(generic_params)[:-1]
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
    if use_vunit:
        template_fn = os.path.join(os.path.dirname(__file__), 'templates',
                                'file_testbench.vhd')
    else:
        template_fn = os.path.join(os.path.dirname(__file__), 'templates',
                                'file_testbench_no_vunit.vhd')
    if add_double_wrapper:
        dut_name = enty.identifier + '_toslvcodec'
    else:
        dut_name = enty.identifier
    with open(template_fn, 'r') as f:
        filetestbench_template = jinja2.Template(f.read())
    filetestbench = filetestbench_template.render(
        test_name='{}_tb'.format(enty.identifier),
        use_clauses=use_clauses,
        generic_params=generic_params,
        definitions=definitions,
        dut_generics=dut_generics,
        dut_name=dut_name,
        clk_connections=clk_connections,
        connections=connections,
        output_path=default_output_path,
        )
    return filetestbench


def prepare_files(directory, filenames, top_entity, add_double_wrapper=False, use_vunit=True,
                  dut_directory=None, default_generics=None, default_output_path=None):
    '''
    Parses VHDL files, and generates a testbench for `top_entity`.
    Returns a tuple of a list of testbench files, and a dictionary
    of parsed objects.
    '''
    dut_fns = filenames[:]
    if dut_directory is None:
        dut_directory = directory
    entities, packages = vhdl_parser.parse_and_resolve_files(filenames)
    resolved_entity = entities[top_entity]
    if use_vunit:
        tb_fns = [os.path.join(config.vhdldir, 'read_file.vhd')]
    else:
        tb_fns = [os.path.join(config.vhdldir, 'read_file_no_vunit.vhd')]
    tb_fns += [
        os.path.join(config.vhdldir, 'write_file.vhd'),
        os.path.join(config.vhdldir, 'clock.vhd'),
    ]
    # Make file testbench
    ftb = make_filetestbench(resolved_entity, add_double_wrapper, use_vunit=use_vunit,
                             default_generics=default_generics,
                             default_output_path=default_output_path,)
    ftb_fn = os.path.join(directory, '{}_tb.vhd'.format(
        resolved_entity.identifier))
    with open(ftb_fn, 'w') as f:
        f.write(ftb)
    if add_double_wrapper:
        fromslvcodec_wrapper, toslvcodec_wrapper = make_double_wrapper(resolved_entity, default_generics=default_generics)
        fromslvcodec_fn = os.path.join(dut_directory, resolved_entity.identifier + '_fromslvcodec.vhd')
        toslvcodec_fn = os.path.join(directory, resolved_entity.identifier + '_toslvcodec.vhd')
        with open(fromslvcodec_fn, 'w') as f:
            f.write(fromslvcodec_wrapper)
            dut_fns.append(fromslvcodec_fn)
        with open(toslvcodec_fn, 'w') as f:
            f.write(toslvcodec_wrapper)
            tb_fns.append(toslvcodec_fn)
    tb_fns.append(ftb_fn)
    resolved = {
        'entities': entities,
        'packages': packages,
        }
    return tb_fns, dut_fns, resolved


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
