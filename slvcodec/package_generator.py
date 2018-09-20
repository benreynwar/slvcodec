'''
Functions to generate packages from existing packages that define types to
convert the types back and forth to std_logic_vector.
'''

import os
import logging

import jinja2

from slvcodec import typs, math_parser


logger = logging.getLogger(__name__)


declarations_template = '''  constant {type.identifier}_slvcodecwidth: natural := {width_expression};
  function to_slvcodec (constant data: {type.identifier}) return std_logic_vector;
  function from_slvcodec (constant slv: std_logic_vector) return {type.identifier};'''

width_declarations_template = '''  constant {type.identifier}_slvcodecwidth: natural := {width_expression};'''

functions_declarations_template = '''  function to_slvcodec (constant data: {type.identifier}) return std_logic_vector;
  function from_slvcodec (constant slv: std_logic_vector) return {type.identifier};'''


def make_record_declarations_and_definitions(record_type):
    '''
    Create declarations and definitions of functions to convert to and from
    record types.
    '''
    declarations = declarations_template.format(
        type=record_type,
        width_expression=math_parser.str_expression(record_type.width),
    )
    template_fn = os.path.join(os.path.dirname(__file__), 'templates',
                               'slvcodec_record_template.vhd')
    with open(template_fn, 'r') as f:
        definitions_template = jinja2.Template(f.read())
        indices_names_and_widths = []
    for index, name_and_subtype in enumerate(record_type.names_and_subtypes):
        name, subtype = name_and_subtype
        indices_names_and_widths.append(
            (index, name, math_parser.str_expression(subtype.width)))
    definitions = definitions_template.render(
        type=record_type.identifier,
        indices_names_and_widths=indices_names_and_widths)
    return declarations, definitions


def make_enumeration_declarations_and_definitions(enumeration_type):
    '''
    Create declarations and definitions of functions to convert to and from
    enumeration types.
    '''
    declarations = declarations_template.format(
        type=enumeration_type,
        width_expression=math_parser.str_expression(enumeration_type.width),
    )
    template_fn = os.path.join(os.path.dirname(__file__), 'templates',
                               'slvcodec_enumeration_template.vhd')
    with open(template_fn, 'r') as f:
        definitions_template = jinja2.Template(f.read())
        definitions = definitions_template.render(
            type=enumeration_type.identifier,
            literals=enumeration_type.literals,
            n_literals=len(enumeration_type.literals),
        )
    return declarations, definitions


def make_array_declarations_and_definitions(array_type):
    '''
    Create declarations and definitions of functions to convert to and from
    array types.
    '''
    if hasattr(array_type, 'size'):
        width_expression = math_parser.str_expression(array_type.width)
        width_declaration = width_declarations_template.format(
            type=array_type,
            width_expression=width_expression,
        )
        if array_type.unconstrained_type.identifier is None:
            subtype_width = math_parser.str_expression(
                array_type.unconstrained_type.subtype.width)
            unconstrained = False
        else:
            # We don't need to define functions because it's not a new kind of
            # array it's just constraining an existing one.
            subtype_width = None
    else:
        width_declaration = ''
        unconstrained = True
        if array_type.subtype.identifier is None:
            subtype_width = math_parser.str_expression(
                array_type.subtype.width)
        else:
            subtype_width = array_type.subtype.identifier + '_slvcodecwidth'

    # Define functions unless we have defined size and subtype has identifier
    if subtype_width is None:
        # No functions to define.
        declarations = width_declaration
        definitions = ''
    else:
        functions_declarations = functions_declarations_template.format(
            type=array_type)
        declarations = '\n'.join([width_declaration, functions_declarations])
        template_fn = os.path.join(os.path.dirname(__file__), 'templates',
                                   'slvcodec_array_template.vhd')
        with open(template_fn, 'r') as template_file:
            definitions_template = jinja2.Template(template_file.read())
        definitions = definitions_template.render(
            type=array_type.identifier,
            subtype_width=subtype_width,
            unconstrained=unconstrained,
            )
    return declarations, definitions


def make_declarations_and_definitions(typ):
    '''
    Create declarations and definitions of functions to convert to and from
    array and record types.  Other types are not yet supported.
    '''
    if type(typ) in (typs.Array, typs.ConstrainedArray,
                     typs.ConstrainedStdLogicVector, typs.ConstrainedUnsigned,
                     typs.ConstrainedSigned):
        d_and_d = make_array_declarations_and_definitions(typ)
    elif isinstance(typ, typs.Record):
        d_and_d = make_record_declarations_and_definitions(typ)
    elif isinstance(typ, typs.Enumeration):
        d_and_d = make_enumeration_declarations_and_definitions(typ)
    else:
        logger.warning('Dont know how to slvcodec functions for {}.'.format(typ))
        d_and_d = '', ''
    return d_and_d


def make_slvcodec_package(pkg):
    '''
    Create a package containing functions to convert to and from
    std_logic_vector.  A package is taken as an input, all the types
    are parsed from it and the converting functions generated.
    '''
    all_declarations = []
    all_definitions = []
    for typ in pkg.types.values():
        declarations, definitions = make_declarations_and_definitions(typ)
        all_declarations.append(declarations)
        all_definitions.append(definitions)
    combined_declarations = '\n'.join(all_declarations)
    combined_definitions = '\n'.join(all_definitions)
    use_lines = []
    libraries = ['ieee']
    for use in pkg.uses.values():
        if use.library not in  ('ieee', 'std'):
            use_lines.append('use {}.{}.{};'.format(
                use.library, use.design_unit, use.name_within))
            use_lines.append('use work.{}_slvcodec.all;'.format(
                use.design_unit))
        if use.library not in libraries:
            libraries.append(use.library)
    use_lines.append('use ieee.std_logic_1164.all;'.format(pkg.identifier))
    use_lines.append('use ieee.numeric_std.all;'.format(pkg.identifier))
    use_lines.append('use work.{}.all;'.format(pkg.identifier))
    use_lines.append('use work.slvcodec.all;'.format(pkg.identifier))
    library_lines = ['library {};'.format(library) for library in libraries]
    package_template = """{library_lines}
{use_lines}

package {package_name} is

{declarations}

end package;
"""
    package_body_template = """
package body {package_name} is

{definitions}

end package body;
"""
    slvcodec_pkg = package_template.format(
        library_lines='\n'.join(library_lines),
        use_lines='\n'.join(use_lines),
        package_name=pkg.identifier+'_slvcodec',
        declarations=combined_declarations,
        )
    if combined_definitions:
        slvcodec_pkg += package_body_template.format(
            package_name=pkg.identifier+'_slvcodec',
            definitions=combined_definitions,
            )
    return slvcodec_pkg
