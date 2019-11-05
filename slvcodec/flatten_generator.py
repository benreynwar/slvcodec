import logging
import os

import jinja2

from slvcodec import entity, typs, package_generator, config, vhdl_parser, math_parser

logger = logging.getLogger(__name__)


def flatten_type(typ, generics=None):
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
    suffix = ''
    for level in hierarchy:
        if isinstance(level, int):
            suffix += '(' + str(level) + ')'
        else:
            suffix += '.' + level
    return suffix


def make_flat_wrapper(enty, wrapped_name, separator= '_', generics=None):
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
