import os
import jinja2

from vunit import vhdl_parser

from slvcodec import typs, package, symbolic_math

declarations_template = '''  constant {type.identifier}_width: natural := {width_expression};
  function to_slvcodec (constant data: {type.identifier}) return std_logic_vector;
  function from_slvcodec (constant slv: std_logic_vector) return {type.identifier};'''

unconstrained_declarations_template = '''  function to_slvcodec (constant data: {type.identifier}) return std_logic_vector;
  function from_slvcodec (constant slv: std_logic_vector) return {type.identifier};'''

constrained_declarations_template = '''  constant {type.identifier}_width: natural := {width_expression};'''


def make_record_declarations_and_definitions(record_type):
    declarations = declarations_template.format(
        type=record_type,
        width_expression=symbolic_math.str_expression(record_type.width),
        )
    template_fn = os.path.join(os.path.dirname(__file__), 'templates', 'slvcodec_record_template.vhd')
    with open(template_fn, 'r') as f:
        definitions_template = jinja2.Template(f.read())
    indices_names_and_widths = []
    for index, name_and_subtype in enumerate(record_type.names_and_subtypes):
        name, subtype = name_and_subtype
        indices_names_and_widths.append(
            (index, name, symbolic_math.str_expression(subtype.width)))
    definitions = definitions_template.render(
        type=record_type.identifier,
        indices_names_and_widths=indices_names_and_widths)
    return declarations, definitions


def make_array_declarations_and_definitions(array_type):
    if hasattr(array_type, 'size'):
        declarations = constrained_declarations_template.format(
            type=array_type,
            width_expression=symbolic_math.str_expression(array_type.width),
            )
        definitions = ''
    else:
        declarations = unconstrained_declarations_template.format(
            type=array_type
            )
        template_fn = os.path.join(os.path.dirname(__file__), 'templates', 'slvcodec_array_template.vhd')
        with open(template_fn, 'r') as f:
            definitions_template = jinja2.Template(f.read())
        definitions = definitions_template.render(
            type=array_type.identifier,
            subtype=array_type.subtype,
            )
    return declarations, definitions


def make_integer_declarations_and_definitions(integer_type):
    if hasattr(integer_type, 'width'):
        declarations = constrained_declarations_template.format(
            type=integer_type,
            width_expression=symbolic_math.str_expression(integer_type.width),
            )
        definitions = ''
    else:
        declarations = unconstrained_declarations_template.format(
            type=integer_type
            )
        template_fn = os.path.join(os.path.dirname(__file__), 'templates', 'slvcodec_integer_template.vhd')
        with open(template_fn, 'r') as f:
            definitions_template = jinja2.Template(f.read())
        definitions = definitions_template.render(
            type=integer_type.identifier,
            subtype=integer_type.subtype,
            )
    return declarations, definitions


def make_declarations_and_definitions(typ):
    if type(typ) in (typs.Array, typs.ConstrainedArray,
                     typs.ConstrainedStdLogicVector):
        return make_array_declarations_and_definitions(typ)
    elif isinstance(typ, typs.Record):
        return make_record_declarations_and_definitions(typ)
    elif type(typ) in (typs.ConstrainedInteger,):
        return make_integer_declarations_and_definitions(typ)
    elif isinstance(typ, typs.Enum):
        return make_record_declarations_and_definitions(typ)
    else:
        raise Exception('Unknown typ {}'.format(typ))


def make_slvcodec_package(pkg):
    all_declarations = []
    all_definitions = []
    for typ in pkg.types.values():
        declarations, definitions = make_declarations_and_definitions(typ)
        all_declarations.append(declarations)
        all_definitions.append(definitions)
    combined_declarations = '\n'.join(all_declarations)
    combined_definitions = '\n'.join(all_definitions)
    use_lines = []
    libraries = []
    for use in pkg.uses.values():
        use_lines.append('use {}.{}.{};'.format(
            use.library, use.design_unit, use.name_within))
        if use.library not in libraries:
            libraries.append(use.library)
    use_lines.append('use ieee.numeric_std.all;'.format(pkg.identifier))
    use_lines.append('use work.{}.all;'.format(pkg.identifier))
    use_lines.append('use work.slvcodec.all;'.format(pkg.identifier))
    library_lines = ['library {};'.format(library) for library in libraries]
    template = """{library_lines}
{use_lines}

package {package_name} is

{declarations}

end package;

package body {package_name} is

{definitions}

end package body;
"""
    slvcodec_pkg = template.format(
        library_lines='\n'.join(library_lines),
        use_lines='\n'.join(use_lines),
        package_name=pkg.identifier+'_slvcodec',
        declarations=combined_declarations,
        definitions=combined_definitions,
        )
    return slvcodec_pkg


def get_base_name(filename):
    allowed_suffixes = ('.vhd', '.vhdl')
    base_filename = os.path.basename(filename)
    matches_suffix = [base_filename[:-len(suffix)] for suffix in allowed_suffixes
                      if base_filename[-len(suffix):] == suffix]
    if not matches_suffix:
        raise ValueError('Suffix in filename {} must be in {}'.format(
            filename, allowed_suffixes))
    base_name = matches_suffix[0]
    return base_name


def write_package(base_package_filename, slvcodec_package_filename=None,
                  required_package_filenames=[]):
    required_packages = package.process_packages(required_package_filenames)
    parsed_package = package.parsed_package_from_filename(base_package_filename)
    processed_package = package.process_parsed_package(parsed_package)
    pkg = processed_package.resolve(required_packages)
    slvcodec_pkg = make_slvcodec_package(pkg)
    if slvcodec_package_filename is None:
        base_name = get_base_name(base_package_filename)
        slvcodec_package_filename = os.path.join(
            os.path.dirname(base_package_filename), base_name + '_slvcodec.vhd')
    with open(slvcodec_package_filename, 'w') as f:
        f.write(slvcodec_pkg)
    return slvcodec_package_filename


if __name__ == '__main__':
    fn = write_package('tests/vhdl_type_pkg.vhd', 'deleteme.vhd')
    print(fn)
