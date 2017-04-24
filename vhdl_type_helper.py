import re

from vunit import vhdl_parser


def parse(package):
    # Get all the types and constants in the package.
    # Check if any types or constants have undefined dependencies.
    # Update the widths and values for any constants that have met dependencies.
    # Keep iterating until nothing changes.
    # Exception is anything is left undefined.
    pass


def int_if_possible(v):
    try:
        i = int(v)
    except ValueError:
        i = None
    return i


def multiplication(a, b):
    a_int = int_if_possible(a)
    b_int = int_if_possible(b)
    if (a_int is None) or (b_int is None):
        multiplied = '{} * {}'.format(a, b)
    else:
        multiplied = str(a_int * b_int)
    return multiplied


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
        high_int = int_if_possible(high)
        low_int = int_if_possible(low)
        if high_int is None or low_int is None:
            size = '({}+1 - {})'.format(high, low)
        else:
            size = str(high_int + 1 - low_int)
    else:
        size = None
    return size


def get_size(typ):
    if typ.range2.range_type is not None:
        raise Exception('Cannot handle 2d arrays yet')
    range_type_mark = typ.range1.range_type
    if typ.range1.left is None and typ.range1.right is None:
        left, right = None, None
        size = None
    else:
        left, right = typ.range1.left, typ.range1.right
        size = '({}+1 - {})'.format(left, right)
    return size


def process_array_subtype(typ, processed_types):
    subtype_mark = typ.subtype_indication.type_mark
    subtype = processed_types.get(subtype_mark, None)
    if subtype is None:
        success = False
    else:
        assert(not subtype.constrained)
        typ.subtype_width_constant = subtype.subtype_width_constant
        size = get_size(typ)
        if size is None:
            raise Exception('Array subtype must be constrained.')
        else:
            typ.constrained = True
            typ.width = multiplication(typ.subtype_width_constant, size)
            typ.width_constant = '{}_width'.format(typ.identifier)
        success = True
    typ.subtype = subtype_mark
    return success


def process_array_type(typ, processed_types):
    subtype_mark = typ.subtype_indication.type_mark
    subtype = processed_types.get(subtype_mark, None)
    if subtype is None:
        success = False
    else:
        typ.subtype_width_constant = subtype.width_constant
        size = get_size(typ)
        if size is None:
            typ.constrained = False
        else:
            typ.constrained = True
            typ.width_constant = multiplication(type.subtype_width_constant, size)
        success = True
    typ.subtype = subtype_mark
    return success


def process_record_type(typ, processed_types):
    subtype_marks = [
        element.subtype_indication.type_mark for element in typ.elements]
    subtypes_ready = all([subtype_mark in processed_types
                          for subtype_mark in subtype_marks])

    for subtype_mark in subtype_marks:
        subtypes = processed_types.get(subtype_mark, None)
    if not subtypes_ready:
        success = False
    else:
        subtypes = [processed_types[subtype_mark] for subtype_mark in subtype_marks]
        subtype_widths = []
        subtype_names = []
        for element, subtype in zip(typ.elements, subtypes):
            if hasattr(subtype, 'constrained') and not subtype.constrained:
                size = get_constraint_size(element.subtype_indication.constraint)
                width = multiplication(subtype.subtype_width_constant, size)
            else:
                width = subtype.width_constant
            subtype_widths.append(width)
            identifier_list = element.identifier_list
            assert(len(identifier_list) == 1)
            subtype_names.append(identifier_list[0])
        typ.subtype_widths = subtype_widths
        typ.subtype_names = subtype_names
        typ.width = '(' + ' + '.join(subtype_widths) + ')'
        typ.width_constant = '{}_width'.format(typ.identifier)
        success = True
    return success


def process(typ, processed_types):
    if isinstance(typ, vhdl_parser.VHDLArraySubtype):
        success = process_array_subtype(typ, processed_types)
    elif isinstance(typ, vhdl_parser.VHDLArrayType):
        success = process_array_type(typ, processed_types)
    elif isinstance(typ, vhdl_parser.VHDLRecordType):
        success = process_record_type(typ, processed_types)
    return success


class StdLogic:

    def __init__(self):
        self.width = 1
        self.width_constant = '1'


class StdLogicVector:

    def __init__(self):
        self.subtype_width = 1
        self.subtype_width_constant = '1'
        self.constrained = False


def process_types(types):
    unprocessed_types = [x for x in types]
    processed_types = {
        'std_logic_vector': StdLogicVector(),
        'std_logic': StdLogic(),
        }
    counter = 0
    # Process the types to work out what the widths are.
    while unprocessed_types:
        for typ in unprocessed_types:
            success = process(typ, processed_types)
            if success:
                processed_types[typ.identifier] = typ
        counter += 1
        unprocessed_types = [x for x in types if x.identifier not in processed_types]
        if counter == 100:
            raise Exception('Hit iteration limit ({}).  Could not process {}'.format(
                counter, unprocessed_types))


if __name__ == '__main__':
    with open('vhdl_type_pkg.vhd', 'r') as f:
        code = f.read()
    parsed = vhdl_parser.VHDLParser.parse(code, None)
    package = parsed.packages[0]
    types = package.array_subtypes + package.array_types + package.record_types
    # Create the package with the conversions to and from slvs.
    process_types(types)
    for typ in types:
        if hasattr(typ, 'constrained') and not typ.constrained:
            print(typ.identifier, 'unconstrained')
        else:
            print(typ.identifier, typ.width)
