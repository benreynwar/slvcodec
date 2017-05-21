import re

from vunit import vhdl_parser

from slvcodec import symbolic_math, typs


def process_parsed_type(typ):
    if isinstance(typ, vhdl_parser.VHDLArraySubtype):
        success = process_array_subtype(typ)
    elif isinstance(typ, vhdl_parser.VHDLArrayType):
        success = process_array_type(typ)
    elif isinstance(typ, vhdl_parser.VHDLRecordType):
        success = process_record_type(typ)
    return success


def get_size(typ):
    if typ.range2.range_type is not None:
        raise Exception('Cannot handle 2d arrays yet')
    if typ.range1.left is None and typ.range1.right is None:
        size = None
    else:
        left_expression = symbolic_math.string_to_expression(typ.range1.left)
        right_expression = symbolic_math.string_to_expression(typ.range1.right)
        size = symbolic_math.simplify(symbolic_math.Addition([
            symbolic_math.Term(number=n, expression=e) for n ,e in
            ((1, left_expression), (1, 1), (-1, right_expression))]))
    return size


def get_constraint_size(constraint):
    _constrained_range_re = re.compile(r"""
        \s*\(
        \s*(?P<range_left>.+?)
        \s+(?P<direction>to|downto)\s+
        (?P<range_right>.+?)\s*
        \)\s*""", re.MULTILINE | re.IGNORECASE | re.VERBOSE | re.DOTALL)
    match = _constrained_range_re.match(constraint)
    if match:
        gd = match.groupdict()
        if gd['direction'] == 'to':
            high = gd['range_right']
            low = gd['range_left']
        elif gd['direction'] == 'downto':
            high = gd['range_left']
            low = gd['range_right']
        size_as_string = '{} + 1 - {}'.format(high, low)
        size = symbolic_math.parse_and_simplify(size_as_string)
    else:
        raise Exception('Failed to parse constraint.')
    return size


def process_array_subtype(typ):
    subtype_mark = typ.subtype_indication.type_mark
    size = get_size(typ)
    if size is None:
        raise Exception('Array subtype must be constrained.')
    if subtype_mark == 'std_logic_vector':
        processed = typs.UnresolvedConstrainedStdLogicVector(
            identifier=typ.identifier,
            size=size,
        )
    else:
        processed = typs.UnresolvedConstrainedArray(
            identifier=typ.identifier,
            unconstrained_type_identifier=subtype_mark,
            size=size,
            )
    return processed


def process_array_type(typ):
    subtype_mark = typ.subtype_indication.type_mark
    size = get_size(typ)
    if size is None:
        processed = typs.UnresolvedArray(
            identifier=typ.identifier,
            subtype_identifier=subtype_mark,
            )
    else:
        processed = typs.UnresolvedConstrainedArray(
            identifier=typ.identifier,
            subtype_identifier=subtype_mark,
            size=size,
            )
    return processed


def process_subtype_indication(subtype_indication):
    constraint = subtype_indication.constraint
    type_mark = subtype_indication.type_mark
    if not constraint:
        subtype = type_mark
    else:
        subtype = typs.UnresolvedConstrainedArray(
            identifier=None,
            unconstrained_type_identifier=type_mark,
            size=get_constraint_size(constraint),
            )
    return subtype


def process_record_type(typ):
    constrained_subtypes = [
        process_subtype_indication(element.subtype_indication)
        for element in typ.elements]
    names_and_subtypes = [
        (element.identifier_list[0], subtype)
        for element, subtype in zip(typ.elements, constrained_subtypes)]
    processed = typs.UnresolvedRecord(
        typ.identifier,
        names_and_subtypes,
        )
    return processed
