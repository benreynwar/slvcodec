'''
Representations of unresolved and resolved types.

An unresolved type is a description of a type but contains references to other types
and constants are strings.

The unresolved type is resolved so that these references are replaced with the
resolved type and constant objects.
'''


import logging

from slvcodec import math_parser, conversions, resolution


logger = logging.getLogger(__name__)


class ToSlvError(Exception):
    pass


class Generic:
    '''
    A generic parameter.  When the generic cannot be resolved this object
    is used in the expression until resolution is possible.
    '''

    def __init__(self, name, typ, default=None):
        self.name = name
        self.typ = typ
        self.default = default

    def str_expression(self):
        '''
        Returns the a string representation of the math object.  In this case the
        name of the generic parameter.
        '''
        return self.name


def make_substitute_generics_function(d):
    '''
    Makes a function that replaces 'Generic' objects with the appropriate
    value from the dictionary 'd'.
    '''
    def substitute(item):
        if isinstance(item, Generic):
            o = d.get(item.name, item)
        else:
            o = math_parser.transform(item, substitute)
        return o
    return substitute


def apply_generics(generics, expression):
    '''
    Resolve generic objects in the expression.
    '''
    substituted = make_substitute_generics_function(generics)(expression)
    value = math_parser.get_value(substituted)
    return value


class Constant:
    '''
    A constant connected to an expression or value that defines it.
    '''

    def __init__(self, name, expression):
        self.name = name
        self.expression = expression

    def value(self):
        '''
        Determine the value of this constant.
        '''
        return math_parser.get_value(self.expression)

    def str_expression(self):
        '''
        Returns the a string representation of the math object.  In this case the
        name of the constant.
        '''
        return self.name


def resolve_expression(expression, constants):
    '''
    Replace all strings in an expression with the appropriate `Constant`
    objects.
    '''
    constant_dependencies = math_parser.get_constant_list(expression)
    missing_constants = set(constant_dependencies) - set(constants.keys())
    if missing_constants:
        raise resolution.ResolutionError('Missing constants {}'.format(missing_constants))
    if constant_dependencies:
        resolved_e = math_parser.make_substitute_function(constants)(expression)
    else:
        resolved_e = expression
    return resolved_e


class StdLogic:
    '''
    A python descriptions of the std_logic vhdl type.
    '''

    width = 1
    resolved = True
    unconstrained = False

    def __str__(self):
        return 'std_logic'

    def to_slv(self, data, generics, allow_undefined=True):
        '''
        Convert the data into a string on '0's and '1's.
        '''
        if data not in (0, 1, None):
            raise ToSlvError('Value received for std_logic is {}.  '.format(data) +
                             'Allowed values are 0, 1 or None.')
        if data == 1:
            slv = '1'
        elif data == 0:
            slv = '0'
        else:
            assert allow_undefined
            slv = 'U'
        return slv

    def from_slv(self, slv, generics):
        '''
        Convert a string of '0's and '1's into the data object.
        '''
        mapping = {
            '0': 0,
            '1': 1,
            }
        data = mapping.get(slv, None)
        return data

    def reduce_slv(self, slv, generics):
        '''
        Extracts the data object from the end of the given 'slv'.
        Returns a (data_object, remainder_slv) tuple.
        '''
        return self.from_slv(slv[-1], generics), slv[:-1]


std_logic = StdLogic()


class UnresolvedConstrainedArray:
    '''
    An array with a constrained length, but where the types and constants
    that define it are not yet resolved.
    '''

    resolved = False
    unconstrained = False

    def __init__(self, identifier, size, unconstrained_type_identifier=None,
                 unconstrained_type=None):
        self.identifier = identifier
        assert (unconstrained_type_identifier is None) or (unconstrained_type is None)
        assert not ((unconstrained_type_identifier is None) and (unconstrained_type is None))
        self.unconstrained_type = unconstrained_type
        self.unconstrained_type_identifier = unconstrained_type_identifier
        if unconstrained_type_identifier is not None:
            self.type_dependencies = [self.unconstrained_type_identifier]
        else:
            self.type_dependencies = self.unconstrained_type.type_dependencies
        self.size = size

    def resolve(self, types, constants):
        '''
        Replace references to types and constants to resolved types and constants.
        `types`: a dictionary of resolved types.
        `constants`: a dictionary of resolved constants.
        '''
        if self.unconstrained_type_identifier is not None:
            if self.unconstrained_type_identifier not in types:
                raise resolution.ResolutionError(
                    '{} is not a known type.'.format(self.unconstrained_type_identifier))
            unconstrained_type = types[self.unconstrained_type_identifier]
        else:
            unconstrained_type = self.unconstrained_type.resolve(types, constants)
        size = resolve_expression(self.size, constants)
        return ConstrainedArray(
            identifier=self.identifier,
            unconstrained_type=unconstrained_type,
            size=size,
            constants=constants
            )


class ConstrainedArray:
    '''
    An array with a constrained length.  The types and constants that define
    it have been resolved.
    '''

    resolved = True
    unconstrained = False

    def __init__(self, identifier, unconstrained_type, size, constants):
        self.identifier = identifier
        self.unconstrained_type = unconstrained_type
        self.size = size
        self.width = math_parser.Multiplication(
            powers=(math_parser.Power(number=1, expression=self.size),
                    math_parser.Power(number=1, expression=self.unconstrained_type.subtype.width),
                   ))

    def __str__(self):
        if self.identifier is None:
            assert self.unconstrained_type.identifier is not None
            s = '{}({}-1 downto 0)'.format(
                self.unconstrained_type.identifier, math_parser.str_expression(
                    self.size))
        else:
            s = self.identifier
        return s

    def to_slv(self, data, generics, allow_undefined=True):
        size = apply_generics(generics, self.size)
        if data is None:
            assert allow_undefined
            data = [None] * size
        try:
            if len(data) != size:
                raise ToSlvError('Length {} does not match expected length {}.'.format(
                    len(data), size))
        except TypeError as e:
            raise ToSlvError('Data is "{}" and does not have a length.  Expected length is {}.'.format(
                data, size)) from e
        slv = self.unconstrained_type.to_slv(data, generics, allow_undefined)
        return slv

    def reduce_slv(self, slv, generics):
        width = int(apply_generics(generics, self.width))
        if width == 0:
            these_slv = slv[:0]
            reduced_slv = slv[0:]
        else:
            these_slv = slv[-width:]
            reduced_slv = slv[:-width]
        data = self.from_slv(these_slv, generics)
        return data, reduced_slv

    def from_slv(self, slv, generics):
        data = self.unconstrained_type.from_slv(slv, generics)
        size = apply_generics(generics, self.size)
        assert len(data) == size
        return data


class UnresolvedArray:
    '''
    An array without defined length and with types and constant unresolved.
    '''

    resolved = False
    unconstrained = True

    def __init__(self, identifier, subtype_identifier=None, subtype=None):
        assert (subtype is None) or (subtype_identifier is None)
        assert (subtype is not None) or (subtype_identifier is not None)
        self.identifier = identifier
        self.subtype_identifier = subtype_identifier
        self.subtype = subtype
        if self.subtype is not None:
            self.type_dependencies = self.subtype.type_dependencies
        else:
            self.type_dependencies = [self.subtype_identifier]

    def resolve(self, types, constants):
        if self.subtype is not None:
            subtype = self.subtype.resolve(types, constants)
        else:
            subtype = types.get(self.subtype_identifier)
        return Array(
            identifier=self.identifier,
            subtype=subtype,
            )


class Array:
    '''
    An array without defined length and with types and constant resolved.
    '''

    resolved = True
    unconstrained = True

    def __init__(self, identifier, subtype):
        self.identifier = identifier
        self.subtype = subtype

    def to_slv(self, data, generics, allow_undefined=True):
        if data is None:
            raise ToSlvError('Cannot convert None to binary for an unconstrained array.')
        slv = ''.join([self.subtype.to_slv(d, generics, allow_undefined)
                       for d in reversed(data)])
        return slv

    def from_slv(self, slv, generics):
        w = apply_generics(generics, self.subtype.width)
        intw = int(w)
        assert intw == w
        assert len(slv) % intw == 0
        n = len(slv)//intw
        assert n * intw == len(slv)
        slv_pieces = [slv[i*intw: (i+1)*intw] for i in range(n)]
        data = list(reversed([self.subtype.from_slv(piece, generics) for piece in slv_pieces]))
        return data


class StdLogicVector(Array):
    '''
    A python description of the std_logic_vector type.
    '''

    def __init__(self):
        Array.__init__(self, identifier='std_logic_vector', subtype=std_logic)


std_logic_vector = StdLogicVector()


class UnresolvedConstrainedStdLogicVector(StdLogicVector):
    '''
    A std_logic_vector with a defined length but with the constants that
    define the length unresolved.
    '''

    resolved = False
    type_dependencies = tuple()
    unconstrained = False

    def __init__(self, identifier, size):
        self.identifier = identifier
        self.size = size
        self.width = size

    def resolve(self, types, constants):
        size = resolve_expression(self.size, constants)
        resolved = ConstrainedStdLogicVector(
            identifier=self.identifier, size=size)
        return resolved


class ConstrainedStdLogicVector:
    '''
    A std_logic_vector with a defined length, with the constants that
    define the length resolved.
    '''

    unconstrained_name = 'std_logic_vector'
    unconstrained_type = StdLogicVector()
    unconstrained = False

    def __init__(self, identifier, size):
        self.identifier = identifier
        self.size = size
        self.width = size

    def __str__(self):
        if self.identifier is None:
            s = '{}({}-1 downto 0)'.format(
                self.unconstrained_name,
                math_parser.str_expression(self.size))
        else:
            s = self.identifier
        return s

    def to_slv(self, data, generics, allow_undefined=True):
        size = int(apply_generics(generics, self.size))
        if data is None:
            assert allow_undefined
            slv = 'U' * size
        else:
            min_value = 0
            max_value = pow(2, size)-1
            try:
                if (data < min_value) or (data > max_value):
                    raise ToSlvError('Value of {} received for type {}.  Should be in range {} to {}'.format(
                        data, self.identifier, min_value, max_value))
            except TypeError:
                msg = 'Type of data is {}, but we expected a natural integer'.format(type(data))
                raise ToSlvError(msg)
            bits = []
            for i in range(size):
                bits.append(data % 2)
                data = data >> 1
            assert data == 0
            slv = ''.join([std_logic.to_slv(b, generics, allow_undefined) for b in reversed(bits)])
        return slv

    def reduce_slv(self, slv, generics):
        width = int(apply_generics(generics, self.width))
        if width == 0:
            these_slv = slv[:0]
            reduced_slv = slv[0:]
        else:
            these_slv = slv[-width:]
            reduced_slv = slv[:-width]
        data = self.from_slv(these_slv, generics)
        return data, reduced_slv

    def from_slv(self, slv, generics):
        bits = [std_logic.from_slv(c, generics) for c in slv]
        data = 0
        for b in bits:
            if (b is None) or (data is None):
                data = None
            else:
                data = (data << 1) + b
        return data


class Unsigned(StdLogicVector):
    '''
    A python description of the unsigned type.
    '''

    def __init__(self):
        Array.__init__(self, identifier='unsigned', subtype=std_logic)


class UnresolvedConstrainedUnsigned(UnresolvedConstrainedStdLogicVector):
    '''
    A unsigned with a defined length but with the constants that
    define the length unresolved.
    '''

    def resolve(self, types, constants):
        size = resolve_expression(self.size, constants)
        return ConstrainedUnsigned(
            identifier=self.identifier, size=size)


class ConstrainedUnsigned(ConstrainedStdLogicVector):
    '''
    A unsigned with a defined length, with the constants that
    define the length resolved.
    '''

    unconstrained_name = 'unsigned'


class Signed(StdLogicVector):
    '''
    A python description of the signed type.
    '''

    def __init__(self):
        Array.__init__(self, identifier='signed', subtype=std_logic)


class UnresolvedConstrainedSigned(UnresolvedConstrainedStdLogicVector):
    '''
    A signed with a defined length but with the constants that
    define the length unresolved.
    '''

    def resolve(self, types, constants):
        size = resolve_expression(self.size, constants)
        return ConstrainedSigned(
            identifier=self.identifier, size=size)


class ConstrainedSigned(ConstrainedStdLogicVector):
    '''
    A signed with a defined length, with the constants that
    define the length resolved.
    '''

    resolved = True
    unconstrained_name = 'signed'

    def __init__(self, identifier, size):
        self.identifier = identifier
        self.size = size
        self.width = size
        size_value = math_parser.get_value(size)
        self.max_value = pow(2, size_value-1)-1
        self.min_value = -pow(2, size_value-1)

    def to_slv(self, data, generics, allow_undefined):
        size = apply_generics(generics, self.size)
        if data is None:
            assert allow_undefined
            slv = 'U' * size
        else:
            if (data < self.min_value) or (data > self.max_value):
                raise ToSlvError('Value of {} received for type {}.  Should be in range {} to {}'.format(
                    data, self.identifier, self.min_value, self.max_value))
            if data < 0:
                data += pow(2, size)
            slv = ConstrainedUnsigned.to_slv(self, data, generics, allow_undefined)
        return slv

    def from_slv(self, slv, generics):
        size = apply_generics(generics, self.size)
        data = ConstrainedUnsigned.from_slv(self, slv, generics)
        if data is not None:
            if data > self.max_value:
                data -= pow(2, size)
            assert data >= self.min_value
            assert data <= self.max_value
        return data


class UnresolvedRecord:
    '''
    A record with constants that define it unresolved.
    '''

    resolved = False
    unconstrained = False

    def __init__(self, identifier, names_and_subtypes):
        self.identifier = identifier
        self.names_and_subtypes = names_and_subtypes
        subtypes = [nas[1] for nas in names_and_subtypes]
        self.type_dependencies = []
        for subtype in subtypes:
            if hasattr(subtype, 'identifier') and subtype.identifier is None:
                self.type_dependencies += subtype.type_dependencies
            else:
                self.type_dependencies.append(subtype)

    def resolve(self, types, constants):
        names = [nas[0] for nas in self.names_and_subtypes]
        subtypes = [nas[1] for nas in self.names_and_subtypes]
        resolved_subtypes = []
        for subtype in subtypes:
            if hasattr(subtype, 'identifier') and subtype.identifier is None:
                resolved_subtypes.append(subtype.resolve(types, constants))
            else:
                resolved_subtypes.append(types[subtype])
        resolved_names_and_subtypes = [(n, s) for n, s in zip(names, resolved_subtypes)]
        return Record(
            identifier=self.identifier,
            names_and_subtypes=resolved_names_and_subtypes,
            )


class Record:
    '''
    A record with constants that define it resolved.
    '''

    resolved = True
    unconstrained = False

    def __init__(self, identifier, names_and_subtypes):
        self.identifier = identifier
        self.names_and_subtypes = names_and_subtypes
        subtype_widths = [subtype.width for name, subtype in names_and_subtypes]
        self.width = math_parser.simplify(math_parser.Addition([
            math_parser.Term(number=1, expression=e) for e in subtype_widths]))

    def __str__(self):
        return self.identifier

    def to_slv(self, data, generics, allow_undefined=True):
        if data is None:
            data = {}
        invalid_names = set(data.keys()) - set([name for name, subtype in self.names_and_subtypes])
        if invalid_names:
            raise ToSlvError('Unknown element {} in record of type {}.'.format(
                invalid_names, self.identifier))
        slvs = []
        for name, subtype in self.names_and_subtypes:
            try:
                slvs.append(subtype.to_slv(data.get(name, None), generics, allow_undefined))
            except ToSlvError as error:
                message = error.args[0]
                new_message = 'Error in element {} in record of type {}.'.format(
                    name, self.identifier) + '  ' + message
                raise ToSlvError(new_message) from error
        slv = ''.join(reversed(slvs))
        return slv

    def reduce_slv(self, slv, generics):
        reduced_slv = slv
        data = {}
        for name, subtype in self.names_and_subtypes:
            data[name], reduced_slv = subtype.reduce_slv(reduced_slv, generics)
        return data, reduced_slv

    def from_slv(self, slv, generics):
        data, reduced_slv = self.reduce_slv(slv, generics)
        assert reduced_slv == ''
        return data

    def declaration(self):
        lines = ['type {} is'.format(self.identifier)]
        lines += ['record']
        for name, subtype in self.names_and_subtypes:
            lines += ['    {}: {};'.format(name, subtype)]
        lines += ['end record;']
        return '\n'.join(lines)


class Enumeration:
    '''
    A python representation of the enumeration type.
    '''

    resolved = True
    type_dependencies = tuple()
    unconstrained = False

    def __init__(self, identifier, literals):
        self.identifier = identifier
        self.literals = [l.lower() for l in literals]
        self.width = math_parser.logceil(len(literals))

    def __str__(self):
        return self.identifier

    def to_slv(self, data, generics, allow_undefined=True):
        if data is None:
            assert allow_undefined
            slv = 'U' * self.width
        else:
            if data.lower() not in self.literals:
                raise ToSlvError('Enumeration does not contain {}. Options are {}'.format(
                    data.lower(), self.literals))
            index = self.literals.index(data.lower())
            slv = conversions.uint_to_slv(index, self.width, allow_undefined)
        return slv

    def reduce_slv(self, slv, generics):
        reduced_slv = slv[:-self.width]
        index = conversions.slv_to_uint(slv[-self.width:])
        data = self.literals[index]
        return data, reduced_slv

    def from_slv(self, slv, generics):
        data, reduced_slv = self.reduce_slv(slv, generics)
        assert reduced_slv == ''
        return data

    def declaration(self):
        literals = '(' + ', '.join(self.literals) + ')'
        declaration = 'type {} is {};'.format(self.identifier, literals)
        return declaration

    def resolve(self, types, constants):
        '''
        There is nothing to resolve in an Enumeration.
        '''
        return self
