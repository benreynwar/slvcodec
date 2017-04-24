import os
import jinja2

from vunit import vhdl_parser

from slvcodec.vhdl_type_helper import process_types

declarations_template = '''  constant {type.identifier}_width: natural := {type.width};
  function to_slv (constant data: {type.identifier}) return std_logic_vector;
  function from_slv (constant slv: std_logic_vector) return {type.identifier};'''

unconstrained_declarations_template = '''  function to_slv (constant data: {type.identifier}) return std_logic_vector;
  function from_slv (constant slv: std_logic_vector) return {type.identifier};'''

constrained_declarations_template = '''  constant {type.identifier}_width: natural := {type.width};'''


def make_record_declarations_and_definitions(record_type):
    declarations = declarations_template.format(type=record_type)
    template_fn = os.path.join(os.path.dirname(__file__), 'slvcodec_record_template.vhd')
    with open(template_fn, 'r') as f:
        definitions_template = jinja2.Template(f.read())
    indices_names_and_widths = list(zip(
        range(len(record_type.subtype_names)), record_type.subtype_names,
        record_type.subtype_widths))
    definitions = definitions_template.render(
        type=record_type.identifier,
        indices_names_and_widths=indices_names_and_widths)
    return declarations, definitions


def make_array_declarations_and_definitions(array_type):
    if array_type.constrained:
        declarations = constrained_declarations_template.format(type=array_type)
        definitions = ''
    else:
        declarations = unconstrained_declarations_template.format(type=array_type)
        template_fn = os.path.join(os.path.dirname(__file__), 'slvcodec_array_template.vhd')
        with open(template_fn, 'r') as f:
            definitions_template = jinja2.Template(f.read())
        definitions = definitions_template.render(
            type=array_type.identifier,
            subtype=array_type.subtype,
            )
    return declarations, definitions


def make_declarations_and_definitions(typ):
    if (isinstance(typ, vhdl_parser.VHDLArrayType) or
            isinstance(typ, vhdl_parser.VHDLArraySubtype)):
        return make_array_declarations_and_definitions(typ)
    elif isinstance(typ, vhdl_parser.VHDLRecordType):
        return make_record_declarations_and_definitions(typ)
    elif isinstance(typ, vhdl_parser.VHDEnumerationType):
        return make_record_declarations_and_definitions(typ)
    else:
        raise Exception('Unknown typ {}'.format(typ))


def make_slvcodec_package(parsed):
    package = parsed.packages[0]
    types = package.array_subtypes + package.array_types + package.record_types
    process_types(types)
    all_declarations = []
    all_definitions = []
    for typ in package.types:
        declarations, definitions = make_declarations_and_definitions(typ)
        all_declarations.append(declarations)
        all_definitions.append(definitions)
    combined_declarations = '\n'.join(all_declarations)
    combined_definitions = '\n'.join(all_definitions)
    # Work out the libraries and uses
    librarys = set()
    use_lines = []
    for reference in parsed.references:
        if reference.library not in librarys:
            librarys.add(reference.library)
        use_lines.append('use {}.{}.{};'.format(
            reference.library, reference.design_unit, reference.name_within))
    use_lines.append('use work.{}.all;'.format(package.identifier))
    use_lines.append('use work.slvcodec.all;'.format(package.identifier))
    library_lines = ['library {};'.format(library) for library in librarys]
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
        package_name=package.identifier+'_slvcodec',
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


def write_package(base_package_filename, slvcodec_package_filename=None):
    with open(base_package_filename, 'r') as f:
        code = f.read()
    parsed = vhdl_parser.VHDLParser.parse(code, None)
    slvcodec_package = make_slvcodec_package(parsed)
    if slvcodec_package_filename is None:
        base_name = get_base_name(base_package_filename)
        slvcodec_package_filename = os.path.join(
            os.path.dirname(base_package_filename), base_name + '_slvcodec.vhd')
    with open(slvcodec_package_filename, 'w') as f:
        f.write(slvcodec_package)
    return slvcodec_package_filename
