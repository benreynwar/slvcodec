import logging
import os

import jinja2

from slvcodec import entity, typs, package_generator, config, vhdl_parser

logger = logging.getLogger(__name__)


def make_generics_wrapper(enty, generics, wrapped_name, ports_to_remove=None, for_arch_header='',
                          slv_interface=True):
    """
    Create a wrapper around an entity which sets the generic parameters.
    Args:
      `enty`: A resolved entity object parsed from the VHDL.
      `generics`: A dictionary of generics to set.
      `wrapped_name`: The name of the entity that will do the wrapping.
      `ports_to_remove`: These ports will not be connected to the wrapper. 
          Use for output ports that we don't want to expose in the wrapper.
      `for_arch_header`: Text placed at the top of the architecture.  Used for encryption headers.
      `slv_interface`: Convert all ports to std_logic_vector and std_logic in the wrapper's ports.
    """
    if ports_to_remove is None:
        ports_to_remove = []
    if for_arch_header is None:
        for_arch_header = ''
    generics = generics.copy()
    for k, v in generics.items():
        if isinstance(v, str) and (len(v) > 0) and (v[0] not in  ("'", '"')):
            generics[k] = '"' + v + '"'
    # Get the list of generic parameters for the testbench.
    wrapped_generics = ',\n'.join(['{} => {}'.format(g.name, g.name)
                                   for g in enty.generics.values()])
    # Generate use clauses required by the testbench.
    use_clauses = '\n'.join([
        'use {}.{}.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values() if (u.design_unit not in ('std_logic_1164', 'slvcodec')) and 
                                       ('_slvcodec' not in u.design_unit)])
    use_clauses += '\n' + '\n'.join([
        'use {}.{}_slvcodec.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values()
        if u.library not in ('ieee', 'std') and '_slvcodec' not in u.design_unit])
    # Read in the template and format it.
    if slv_interface:
        template_name = 'setgenerics.vhd'
    else:
        template_name = 'setgenerics_not_slv.vhd'
    template_fn = os.path.join(os.path.dirname(__file__), 'templates', template_name)
    with open(template_fn, 'r') as f:
        template = jinja2.Template(f.read())
    wrapper = template.render(
        entity_name=enty.identifier,
        use_clauses=use_clauses,
        wrapped_generics=wrapped_generics,
        wrapped_name=enty.identifier,
        wrapper_name=wrapped_name,
        wrapped_ports=list(enty.ports.values()),
        wrapper_ports=list([e for e in enty.ports.values() if e.name not in ports_to_remove]),
        for_arch_header=for_arch_header,
        )
    template_name = 'setgenerics_pkg.vhd'
    template_fn = os.path.join(os.path.dirname(__file__), 'templates', template_name)
    with open(template_fn, 'r') as f:
        template = jinja2.Template(f.read())
    constant_generics = [
        (g.name, str(g.typ), generics[g.name])
        for g in enty.generics.values()]
    package = template.render(
        use_clauses=use_clauses,
        generics=constant_generics,
        )
    return wrapper, package


def make_double_wrapper(enty, default_generics=None):
    """
    Create a two wrappers around an entity.
    The first wrapper converts all the ports to std_logic_vector and std_logic.
    The second wrapper converts them back to the original types.
    Between these two wrappers is then a convenient place to do synthesis and the output wrapper
    can be used for testing.
    Args:
      `enty`: A resolved entity object parsed from the VHDL.
      `default_generics`: A dictionary of generics to set as default in the wrappers.
    """
    if default_generics is None:
        default_generics = {}
    else:
        default_generics = default_generics.copy()
    for k, v in default_generics.items():
        if isinstance(v, str) and (len(v) > 0) and (v[0] != "'"):
            default_generics[k] = '"' + v + '"'
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
        if u.library not in ('ieee', 'std') and ('_slvcodec' not in u.design_unit) and
        (u.design_unit != 'slvcodec')])
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


def typ_to_slv(typ):
    '''
    Convert a type to a std_logic_vector or std_logic.
    '''
    if isinstance(typ, typs.StdLogic):
        new_typ = typ
    else:
        if isinstance(typ.size, int):
            size=typ.size
        else:
            size = typ.size.value()
        new_typ = typs.ConstrainedStdLogicVector(identifier=None, size=size)
    return new_typ


def make_filetestbench(enty, add_double_wrapper=False, use_vunit=True,
                       default_output_path=None, default_generics=None,
                       use_pipes=False, slv_interface=False, dut_name=None,
                       extra_definitions='', extra_logic='',
                       ):
    '''
    Generate a testbench that reads inputs from a file, and writes outputs to
    a file.
    Args:
      `enty`: A resolved entity object parsed from the VHDL.
      `add_double_wrapper`: Add two wrappers converting to and from std_logic_vector.  This
         is convenient if we want to synthsize the design.
      `use_vunit`: Make a VUnit compatiable testbench.
      `default_output_path`: The default value for the generic that specifies the output path.
      `default_generics`: The default values for the generics of the entity.
      `use_pipes`: If these is True then the testbench uses named pipes for input and output
         rather than just normal files.
      `slv_interface`: Use if the ports in the test_module have already been converted to
         accept std_logic and std_logic_vector.  Also assumes generics have been removed.
      `dut_name`: The name that will be used to instantiate the dut (might be different
                       to enty.identifier if wrappers are involved).
    '''
    if default_generics is None:
        default_generics = {}
    else:
        default_generics = default_generics.copy()
    for k, v in default_generics.items():
        if isinstance(v, str) and (len(v) > 0) and (v[0] != "'"):
            default_generics[k] = '"' + v + '"'
    # Generate a record type for the entity inputs (excluding clock).
    inputs = [p for p in enty.ports.values()
              if p.direction == 'in' and p.name not in entity.CLOCK_NAMES]
    if slv_interface:
        input_names_and_types = [(p.name, typ_to_slv(p.typ)) for p in inputs]
    else:
        input_names_and_types = [(p.name, p.typ) for p in inputs]
    input_record = typs.Record('t_input', input_names_and_types)
    # Generate a record type for the entity outputs.
    outputs = [p for p in enty.ports.values() if p.direction == 'out']
    if slv_interface:
        output_names_and_types = [(p.name, typ_to_slv(p.typ)) for p in outputs]
    else:
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
    if slv_interface:
        use_clauses = 'use work.slvcodec.all;'
    else:
        use_clauses = '\n'.join([
            'use {}.{}.{};'.format(u.library, u.design_unit, u.name_within)
            for u in enty.uses.values()])
        use_clauses += '\n' + '\n'.join([
            'use {}.{}_slvcodec.{};'.format(u.library, u.design_unit, u.name_within)
            for u in enty.uses.values()
            if (u.library not in ('ieee', 'std')) and ('_slvcodec' not in u.design_unit) and
            (u.design_unit not in ('slvcodec',))])
    # Get the list of generic parameters for the testbench.
    generic_params = []
    for g in enty.generics.values():
        as_str = '{}: {}'.format(g.name, g.typ)
        if g.name in default_generics:
            as_str += ' := {}'.format(default_generics[g.name])
        as_str += ';'
        generic_params.append(as_str)
    if not slv_interface:
        generic_params = '\n'.join(generic_params)[:-1]
    else:
        generic_params = ''
    # Combine the input and output record definitions with the slv conversion
    # functions.
    definitions = '\n'.join([
        input_record.declaration(), output_record.declaration(),
        input_slv_declarations, input_slv_definitions,
        output_slv_declarations, output_slv_definitions])
    clk_names = [p.name for p in enty.ports.values()
                 if (p.direction == 'in') and (p.name in entity.CLOCK_NAMES)]
    assert len(clk_names) in (0, 1)
    clk_connections = '\n'.join(['{} => clk,'.format(clk) for clk in clk_names])
    connections = ',\n'.join(['{} => {}.{}'.format(
        p.name, {'in': 'input_data', 'out': 'output_data'}[p.direction], p.name)
                              for p in enty.ports.values() if p.name not in clk_names])
    if not slv_interface:
        dut_generics = ',\n'.join(['{} => {}'.format(g.name, g.name)
                                for g in enty.generics.values()])
    else:
        dut_generics = ''
    # Read in the testbench template and format it.
    if use_vunit:
        template_fn = os.path.join(os.path.dirname(__file__), 'templates',
                                   'file_testbench.vhd')
    elif use_pipes:
        template_fn = os.path.join(os.path.dirname(__file__), 'templates',
                                   'pipe_testbench.vhd')
    else:
        template_fn = os.path.join(os.path.dirname(__file__), 'templates',
                                   'file_testbench_no_vunit.vhd')
    if dut_name is None:
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
        extra_definitions=extra_definitions,
        extra_logic=extra_logic,
        )
    return filetestbench


def process_signals(signals, type_name):
    """
    Generate type declarations and definitions used by the testbench.
    """
    names_and_types = [(p.name, p.typ) for p in signals]
    record = typs.Record(type_name, names_and_types)
    slv_declarations, slv_definitions = package_generator.make_record_declarations_and_definitions(
        record)
    if signals:
        definitions = [record.declaration(), slv_declarations, slv_definitions]
    else:
        # When there are no signals don't bother writing definitions because an
        # empty record definition is not allowed.
        definitions = []
    return {
        'record': record,
        'slv_declarations': slv_declarations,
        'slv_definitions': slv_definitions,
        'definitions': definitions,
        }


def make_use_clauses(enty):
    """
    Generate use clauses required by the testbench.
    """
    use_clauses = '\n'.join([
        'use {}.{}.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values()])
    use_clauses += '\n' + '\n'.join([
        'use {}.{}_slvcodec.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values()
        if u.library not in ('ieee', 'std') and '_slvcodec' not in u.design_unit])
    return use_clauses


def make_generic_params(enty, default_generics=None):
    """
    Generate generic parameters used by the testbench.
    """
    if default_generics is None:
        default_generics = {}
    else:
        default_generics = default_generics.copy()

    generic_params = []
    for k, v in default_generics.items():
        if isinstance(v, str) and (len(v) > 0) and (v[0] != "'"):
            default_generics[k] = '"' + v + '"'

    for g in enty.generics.values():
        as_str = '{}: {}'.format(g.name, g.typ)
        if g.name in default_generics:
            as_str += ' := {}'.format(default_generics[g.name])
        as_str += ';'
        generic_params.append(as_str)
    generic_params = '\n'.join(generic_params)[:-1]
    return generic_params


def make_filetestbench_multiple_clocks(
        enty, clock_domains, add_double_wrapper=False,
        default_output_path=None, default_generics=None,
        clock_periods=None, clock_offsets=None, use_pipes=False):
    '''
    Generate a testbench that reads inputs from a file, and writes outputs to
    a file.
    Args:
      `enty`: A resolved entity object parsed from the VHDL.
      `clock_domains`: An optional dictionary that maps clock_names to the
         signals in their clock domains.
      `add_double_wrapper`: Add two wrappers converting to and from std_logic_vector.  This
         is convenient if we want to synthsize the design.
      `default_output_path`: The default value for the generic that specifies the output path.
      `default_generics`: The default values for the generics of the entity.
      `use_pipes`: If these is True then the testbench uses named pipes for input and output
         rather than just normal files.
    '''
    grouped_ports = enty.group_ports_by_clock_domain(clock_domains)
    definitions = []
    connections = []
    for clock_name, inputs_and_outputs in grouped_ports.items():
        inputs, outputs = inputs_and_outputs
        input_info = process_signals(inputs, 't_{}_inputs'.format(clock_name))
        output_info = process_signals(outputs, 't_{}_outputs'.format(clock_name))
        definitions += input_info['definitions'] + output_info['definitions']
        for p in inputs:
            connections.append('{} => {}_input_data.{}'.format(p.name, clock_name, p.name))
        for p in outputs:
            connections.append('{} => {}_output_data.{}'.format(p.name, clock_name, p.name))

    use_clauses = make_use_clauses(enty)
    generic_params = make_generic_params(enty, default_generics)

    clock_names = list(clock_domains.keys())
    # Combine the input and output record definitions with the slv conversion
    # functions.
    definitions = '\n'.join(definitions)
    clk_connections = '\n'.join(['{} => {}_clk,'.format(clk, clk)
                                 for clk in clock_names])
    connections = ',\n'.join(connections)
    dut_generics = ',\n'.join(['{} => {}'.format(g.name, g.name)
                               for g in enty.generics.values()])
    # Read in the testbench template and format it.
    if use_pipes:
        template_fn = os.path.join(os.path.dirname(__file__), 'templates',
                                   'pipe_testbench.vhd')
    else:
        template_fn = os.path.join(os.path.dirname(__file__), 'templates',
                                   'file_testbench_multiple_clocks.vhd')
    if add_double_wrapper:
        dut_name = enty.identifier + '_toslvcodec'
    else:
        dut_name = enty.identifier
    if clock_periods is None:
        clock_periods = {}
    if clock_offsets is None:
        clock_offsets = {}

    # Check that the first clock has signals.
    # This is important since this is the file that will determine when the
    # simulation terminates.
    assert clock_domains[clock_names[0]]

    clock_infos = [(name, clock_periods.get(name, '10 ns'), clock_offsets.get(name, '0 ns'),
                    len(clock_domains[name]) > 0)
                   for name in clock_names]
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
        clock_names=clock_names,
        clock_infos=clock_infos,
        output_path=default_output_path,
        )
    return filetestbench


def prepare_files(
        directory, filenames, top_entity, add_double_wrapper=False, use_vunit=True,
        dut_directory=None, default_generics=None, default_output_path=None,
        clock_domains=None, clock_periods=None, clock_offsets=None, use_pipes=False,
        slv_interface=False, wrapper_name=None, extra_logic='', extra_definitions='',
        ):
    """
    Parses VHDL files, and generates a testbench for `top_entity`.
    Returns a tuple of a list of testbench files, and a dictionary
    of parsed objects.
    """
    if wrapper_name is None:
        wrapper_name = top_entity
    dut_fns = filenames[:]
    if dut_directory is None:
        dut_directory = directory
    entities, packages = vhdl_parser.parse_and_resolve_files(filenames)
    resolved_entity = entities[top_entity]
    tb_fns = []
    assert not (use_vunit and use_pipes)
    tb_fns.append(os.path.join(config.vhdldir, 'txt_util.vhd'))
    if use_vunit:
        tb_fns += [
            os.path.join(config.vhdldir, 'read_file.vhd'),
            os.path.join(config.vhdldir, 'write_file.vhd'),
        ]
    elif use_pipes:
        tb_fns += [
            os.path.join(config.vhdldir, 'read_pipe.vhd'),
            os.path.join(config.vhdldir, 'write_pipe.vhd'),
        ]
    else:
        tb_fns += [
            os.path.join(config.vhdldir, 'read_file_no_vunit.vhd'),
            os.path.join(config.vhdldir, 'write_file.vhd'),
        ]
    tb_fns += [
        os.path.join(config.vhdldir, 'clock.vhd'),
    ]
    # Make file testbench
    if clock_domains and ((len(clock_domains) > 1) or use_pipes):
        ftb = make_filetestbench_multiple_clocks(
            resolved_entity, clock_domains, add_double_wrapper, default_generics=default_generics,
            default_output_path=default_output_path,
            clock_periods=clock_periods, clock_offsets=clock_offsets, use_pipes=use_pipes)
    else:
        ftb = make_filetestbench(resolved_entity, add_double_wrapper, use_vunit=use_vunit,
                                 default_generics=default_generics,
                                 default_output_path=default_output_path, use_pipes=use_pipes,
                                 slv_interface=slv_interface, dut_name=wrapper_name,
                                 extra_logic=extra_logic, extra_definitions=extra_definitions,
                                 )
    ftb_fn = os.path.join(directory, '{}_tb.vhd'.format(
        resolved_entity.identifier))
    with open(ftb_fn, 'w') as f:
        f.write(ftb)
    if add_double_wrapper:
        fromslvcodec_wrapper, toslvcodec_wrapper = make_double_wrapper(
                resolved_entity, default_generics=default_generics)
        fromslvcodec_fn = os.path.join(
                dut_directory, resolved_entity.identifier + '_fromslvcodec.vhd')
        toslvcodec_fn = os.path.join(directory, resolved_entity.identifier + '_toslvcodec.vhd')
        with open(fromslvcodec_fn, 'w') as f:
            f.write(fromslvcodec_wrapper)
            dut_fns.append(fromslvcodec_fn)
        with open(toslvcodec_fn, 'w') as f:
            f.write(toslvcodec_wrapper)
            tb_fns.append(os.path.join(config.vhdldir, 'slvcodec.vhd'))
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
    parsed_entities, resolved_packages, filename_to_package_name = process_files(
        directory, filenames)
    combined_filenames = add_slvcodec_files_inner(
        directory, filenames, resolved_packages, filename_to_package_name)
    return combined_filenames


def process_files(directory, filenames, entity_names_to_resolve=None):
    processed_filenames = set()
    parsed_packages = []
    filename_to_package_name = {}
    entities_to_resolve = []
    for filename in filenames:
        if filename in processed_filenames:
            continue
        processed_filenames.add(filename)
        try:
            new_parsed_entities, new_parsed_packages = vhdl_parser.parse_file(filename)
            parsed_packages += new_parsed_packages
        except Exception as e:
            logger.error('Catching exception: {}'.format(str(e)))
            logger.error('Failed to parse file: {}'.format(filename))
        if new_parsed_packages:
            assert len(new_parsed_packages) == 1
            filename_to_package_name[filename] = new_parsed_packages[0].identifier
        if new_parsed_entities:
            assert len(new_parsed_entities) == 1
            if ((entity_names_to_resolve is not None) and
                    (new_parsed_entities[0].identifier in entity_names_to_resolve)):
                entities_to_resolve += new_parsed_entities
    resolved_entities, resolved_packages = vhdl_parser.resolve_entities_and_packages(
        entities=entities_to_resolve, packages=parsed_packages)
    return resolved_entities, resolved_packages, filename_to_package_name


def add_slvcodec_files_inner(directory, filenames, packages, filename_to_package_name):
    initial_basenames = {os.path.basename(fn): fn for fn in filenames}
    combined_filenames = [os.path.join(config.vhdldir, 'slvcodec.vhd')]
    combined_basenames = [os.path.basename(fn) for fn in combined_filenames]
    for fn in filenames:
        bn = os.path.basename(fn)
        if fn not in combined_filenames:
            combined_filenames.append(fn)
            if bn in combined_basenames:
                logger.warning('Two files with the same name: {}'.format(bn))
            else:
                combined_basenames.append(bn)
        if (fn in filename_to_package_name) and (fn[-len('slvcodec.vhd'):] != 'slvcodec.vhd'):
            package_name = filename_to_package_name[fn]
            slvcodec_basename = '{}_slvcodec.vhd'.format(package_name)
            if slvcodec_basename not in initial_basenames:
                slvcodec_pkg = package_generator.make_slvcodec_package(packages[package_name])
                slvcodec_package_filename = os.path.join(directory, slvcodec_basename)
                with open(slvcodec_package_filename, 'w') as f:
                    f.write(slvcodec_pkg)
                combined_filenames.append(slvcodec_package_filename)
            else:
                combined_filenames.append(initial_basenames[slvcodec_basename])
    return combined_filenames


def make_add_slvcodec_files_and_setgenerics_wrapper(
        old_name, new_name, generics, ports_to_remove=None, for_arch_header='',
        slv_interface=True, wrapper_base_name='top.vhd'):
    def add_slvcodec_files_and_setgenerics_wrapper(directory, filenames):
        parsed_entities, resolved_packages, filename_to_package_name = process_files(
            directory, filenames)
        combined_filenames = add_slvcodec_files_inner(
            directory, filenames, resolved_packages, filename_to_package_name)
        parsed_entities, resolved_packages, filename_to_package_name = process_files(
            directory, combined_filenames, entity_names_to_resolve=[old_name])
        enty = parsed_entities[old_name]
        setgenerics_wrapper, setgenerics_pkg = make_generics_wrapper(
            enty, generics, new_name, ports_to_remove, for_arch_header,
            slv_interface=slv_interface)
        wrapper_filename = os.path.join(directory, wrapper_base_name)
        package_filename = os.path.join(directory, 'setgenerics_pkg.vhd')
        package_slvcodec_filename = os.path.join(directory, 'setgenerics_pkg_slvcodec.vhd')
        with open(wrapper_filename, 'w') as f:
            f.write(setgenerics_wrapper)
        with open(package_filename, 'w') as f:
            f.write(setgenerics_pkg)
        with open(package_slvcodec_filename, 'w') as f:
            f.write('''package setgenerics_pkg_slvcodec is
            end package;''')
        combined_filenames += [package_filename, package_slvcodec_filename, wrapper_filename]
        return combined_filenames
    return add_slvcodec_files_and_setgenerics_wrapper


def make_formal_wrapper(enty, generics):
    """
    Create a wrapper around an entity which sets the generic parameters.
    Args:
      `enty`: A resolved entity object parsed from the VHDL.
      `generics`: A dictionary of generics to set.
    """
    generics = generics.copy()
    for k, v in generics.items():
        if isinstance(v, str) and (len(v) > 0) and (v[0] not in  ("'", '"')):
            generics[k] = '"' + v + '"'
    # Get the list of generic parameters for the testbench.
    wrapped_generics = ',\n'.join(['{} => {}'.format(g.name, g.name)
                                   for g in enty.generics.values()])
    # Generate use clauses required by the testbench.
    use_clauses = '\n'.join([
        'use {}.{}.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values() if (u.design_unit not in ('std_logic_1164', 'slvcodec')) and 
                                       ('_slvcodec' not in u.design_unit)])
    use_clauses += '\n' + '\n'.join([
        'use {}.{}_slvcodec.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values()
        if u.library not in ('ieee', 'std') and '_slvcodec' not in u.design_unit])

    # Read in the pkg template and format it.
    template_name = 'formal_pkg.vhd'
    template_fn = os.path.join(os.path.dirname(__file__), 'templates', template_name)
    with open(template_fn, 'r') as f:
        template = jinja2.Template(f.read())
    generic_infos = [{'name': g.name, 'type': g.typ, 'value': generics[g.name]}
                     for g in enty.generics.values()]
    pkg = template.render(
        use_clauses=use_clauses,
        generics=generic_infos,
        )

    use_clauses += '\nuse work.formal_pkg.all;'
    # Read in the template and format it.
    template_name = 'formal_wrapper.vhd'
    template_fn = os.path.join(os.path.dirname(__file__), 'templates', template_name)
    with open(template_fn, 'r') as f:
        template = jinja2.Template(f.read())
    wrapper = template.render(
        entity_name=enty.identifier,
        use_clauses=use_clauses,
        wrapped_generics=wrapped_generics,
        dut_name=enty.identifier,
        ports=list(enty.ports.values()),
        )
    return pkg, wrapper
