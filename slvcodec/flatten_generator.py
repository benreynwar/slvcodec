"""
Provides functions to create a wrapper around at VHDL entities that flattens any compound
ports.

e.g.
-- An array port
  i_data: in array_of_data_t(2 downto 0);
-- becomes
  i_data_0: in data_t;
  i_data_1: in data_t;
  i_data_2: in data_t;
-- A record port
  i_complex: in complex_t;
-- becomes
  i_complex_real: in signed(4 downto 0);
  i_complex_imag: in signed(4 downto 0);
"""

import logging
import os

import jinja2

from slvcodec import entity, typs, package_generator, config, vhdl_parser, math_parser

logger = logging.getLogger(__name__)


def flatten_type(typ, generics=None):
    """
    Flattens a type into its components.

    Args:
      `type`: A parsed VHDL type.
      `generics`: Any generics that are required for flattening. (e.g. The bounds of
         an array must be known before flattening.  This implies that fixing generics
         is often required before flattening).

    Result:
      The output is a list of tuples.
      Each tuple corresponds to one of the elements of the flattened type.
      The first item in a tuple is a list of the name components.  They will be used
      later to create the flattening name by joining them with a separator.
      The second item in the tuple is the type of the flattened item.
    """
    if generics is None:
        generics = {}
    if hasattr(typ, 'names_and_subtypes'):
        all_flattened = []
        for name, subtype in typ.names_and_subtypes:
            for flattened_name, flattened_subtype in flatten_type(subtype, generics):
                all_flattened.append(([name] + flattened_name, flattened_subtype))
    # FIXME need to implement array handling.
    elif isinstance(typ, typs.ConstrainedArray):
        all_flattened = []
        subtype = typ.unconstrained_type.subtype
        size = typs.apply_generics(generics, typ.size)
        for index in range(size):
            for flattened_name, flattened_subtype in flatten_type(subtype, generics):
                all_flattened.append(([index] + flattened_name, flattened_subtype))
    else:
        all_flattened = [([], typ)]
    return all_flattened


def make_wrapped_suffix(hierarchy):
    """
    Produces a string that can be used in VHDL to reference the element of the
    compound type.

    Args:
      `hierarchy`: A list of names to get to a component in a compound type.

    e.g. For a port:
         i_complex: in array_of_complex_t(2 downto 0);
         We can get at one of the components with
         hierarchy = [1, 'complex']
         Which references element 1 in that array, and finally
         the 'complex' entry in that record.
         The output of this function would be:
         '(1).complex'
         Which can be used in VHDL to reference that component.
    """
    suffix = ''
    for level in hierarchy:
        if isinstance(level, int):
            suffix += '(' + str(level) + ')'
        else:
            suffix += '.' + level
    return suffix


def make_flat_wrapper(enty, wrapped_name, separator= '_', generics=None):
    """
    Create a wrapper around a VHDL entity that flattens all the ports.

    Args:
      `enty`: A parsed and resolved VHDL entity.
      `wrapper_name`: The name for the geneated wrapper entity.
      `separator`: The separator to use when flattening ports.
      `generics`: Generics are hardwired when flattening.  This is because flattening
          often requires knowledge of the generics for example to determine the length
          of an array.

    Return:
      A string of the VHDL to define the wrapping entity.
    """
    # Generate use clauses required by the testbench.
    use_clauses = '\n'.join([
        'use {}.{}.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values() if (u.design_unit not in ('std_logic_1164', 'slvcodec')) and 
                                       ('_slvcodec' not in u.design_unit)])
    use_clauses += '\n' + '\n'.join([
        'use {}.{}_slvcodec.{};'.format(u.library, u.design_unit, u.name_within)
        for u in enty.uses.values()
        if u.library not in ('ieee', 'std') and '_slvcodec' not in u.design_unit])
    # Get the wrapper ports
    wrapper_ports = []

    for port_name, port in enty.ports.items():
        for subport_hierarchy, subport_type in flatten_type(port.typ, generics):
            if subport_hierarchy:
                subport_suffix = make_wrapped_suffix(subport_hierarchy)
            else:
                subport_suffix = ''
            subport_name = separator.join([port_name] + [str(x) for x in subport_hierarchy])
            if generics is not None:
                width = typs.apply_generics(generics, subport_type.width)
            wrapper_ports.append({
                'name': subport_name,
                'suffix': subport_suffix,
                'typ': subport_type,
                'parent_name': port_name,
                'direction': port.direction,
                'width': math_parser.str_expression(width),
            })
    # Read in the template and format it.
    template_name = 'flatten.vhd'
    template_fn = os.path.join(os.path.dirname(__file__), 'templates', template_name)
    with open(template_fn, 'r') as f:
        template = jinja2.Template(f.read())
    combined_generics = []
    for generic in enty.generics.values():
        value = generics[generic.name]
        if isinstance(value, str):
            if value[0] not in ("'", '"'):
                value = '"' + value + '"'
        combined_generics.append({
            'name': generic.name,
            'typ': generic.typ,
            'value': value,
            })
    wrapper = template.render(
        entity_name=enty.identifier,
        generics=combined_generics,
        wrapped_name=enty.identifier,
        wrapper_name=wrapped_name,
        wrapped_ports=list(enty.ports.values()),
        wrapper_ports=wrapper_ports,
        use_clauses=use_clauses,
        )
    return wrapper
