import re
import logging

from vunit import vhdl_parser

from slvcodec import symbolic_math, typs

logger = logging.getLogger(__name__)


def process_parsed_type(typ):
    if isinstance(typ, vhdl_parser.VHDLSubtype):
        success = process_subtype(typ)
    elif isinstance(typ, vhdl_parser.VHDLArrayType):
        success = process_array_type(typ)
    elif isinstance(typ, vhdl_parser.VHDLRecordType):
        success = process_record_type(typ)
    return success


def get_size(typ):
    if (typ.range2.left is not None) or (typ.range2.right is not None):
        raise Exception('Cannot handle 2D arrays.')
    lower_expression, upper_expression = get_bounds(typ.range1)
    if (lower_expression is None) and (upper_expression is None):
        size = None
    else:
        size = symbolic_math.simplify(symbolic_math.Addition([
            symbolic_math.Term(number=n, expression=e) for n, e in
            ((1, upper_expression), (1, 1), (-1, lower_expression))]))
    return size


def get_bounds(type_range):
    if type_range is None:
        upper = None
        lower = None
    else:
        if type_range.direction == 'to':
            upper = type_range.right
            lower = type_range.left
        elif type_range.direction == 'downto':
            upper = type_range.left
            lower = type_range.right
        else:
            assert(type_range.left is None)
            assert(type_range.right is None)
            upper = None
            lower = None
    if (upper is None) and (lower is None):
        upper_expression = None
        lower_expression = None
    else:
        upper_expression = symbolic_math.parse_and_simplify(upper)
        lower_expression = symbolic_math.parse_and_simplify(lower)
    return lower_expression, upper_expression


def get_constraint_bounds(constraint):
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
        high_expr = symbolic_math.parse_and_simplify(high)
        low_expr = symbolic_math.parse_and_simplify(low)
        size_as_string = '{} + 1 - {}'.format(high, low)
        size = symbolic_math.parse_and_simplify(size_as_string)
    else:
        raise Exception('Failed to parse constraint.')
    return high_expr, low_expr


def get_range_bounds(type_range):
    _type_range_re = re.compile(r"""
        \s*range
        \s*(?P<range_left>.+?)
        \s+(?P<direction>to|downto)\s+
        (?P<range_right>.+?)\s*
        """, re.MULTILINE | re.IGNORECASE | re.VERBOSE | re.DOTALL)
    match = _type_range_re.match(type_range)
    if match:
        gd = match.groupdict()
        if gd['direction'] == 'to':
            high = gd['range_right']
            low = gd['range_left']
        elif gd['direction'] == 'downto':
            high = gd['range_left']
            low = gd['range_right']
        high_expr = symbolic_math.parse_and_simplify(high)
        low_expr = symbolic_math.parse_and_simplify(low)
    else:
        raise Exception('Failed to parse constraint.')
    return low_expr, high_expr


def get_constraint_size(constraint):
    high, low = get_constraint_bounds(constraint)
    size = symbolic_math.parse_and_simplify('{} + 1 - {}'.format(
        symbolic_math.str_expression(high), symbolic_math.str_expression(low)))
    return size


def process_subtype(typ):
    subtype_mark = typ.subtype_indication.type_mark
    size = get_size(typ)
    lower, upper = get_bounds(typ.integer_range)
    if (size is None) and ((lower is None) or (upper is None)):
        raise Exception('Array subtype must be constrained.')
    if subtype_mark == 'std_logic_vector':
        processed = typs.UnresolvedConstrainedStdLogicVector(
            identifier=typ.identifier,
            size=size,
        )
    elif subtype_mark == 'unsigned':
        processed = typs.UnresolvedConstrainedUnsigned(
            identifier=typ.identifier,
            size=size,
        )
    elif subtype_mark == 'signed':
        processed = typs.UnresolvedConstrainedSigned(
            identifier=typ.identifier,
            size=size,
        )
    elif subtype_mark == 'integer':
        processed = typs.UnresolvedConstrainedInteger(
            identifier=typ.identifier,
            upper=upper,
            lower=lower
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
        unconstrained = typs.UnresolvedArray(
            identifier=None,
            subtype_identifier=subtype_mark,
            )
        processed = typs.UnresolvedConstrainedArray(
            identifier=typ.identifier,
            unconstrained_type=unconstrained,
            size=size,
            )
    return processed


def process_subtype_indication(subtype_indication):
    constraint = subtype_indication.constraint
    type_range = subtype_indication.type_range
    type_mark = subtype_indication.type_mark
    if constraint and type_range:
        raise Exception('Subtype indication has constraint and a type range.  Cannot handle this.')
    if constraint:
        size = get_constraint_size(constraint)
    else:
        size = None
    if type_range:
        lower_bound, upper_bound = get_range_bounds(type_range)
    else:
        lower_bound, upper_bound = None, None
    if (not constraint) and (not type_range):
        subtype = type_mark
    else:
        if type_mark == 'std_logic_vector':
            subtype = typs.UnresolvedConstrainedStdLogicVector(
                identifier=None,
                size=size,
                )
        elif type_mark == 'unsigned':
            subtype = typs.UnresolvedConstrainedUnsigned(
                identifier=None,
                size=size,
            )
        elif type_mark == 'signed':
            subtype = typs.UnresolvedConstrainedSigned(
                identifier=None,
                size=size,
            )
        elif type_mark == 'integer':
            subtype = typs.UnresolvedConstrainedInteger(
                identifier=None,
                upper=upper_bound,
                lower=lower_bound
                )
        else:
            subtype = typs.UnresolvedConstrainedArray(
                identifier=None,
                unconstrained_type_identifier=type_mark,
                size=size,
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
