import logging

from slvcodec import symbolic_math

logger = logging.getLogger(__name__)


class Generic:

    def __init__(self, name, typ, default=None):
        self.name = name
        self.typ = typ
        self.default = default

    def str_expression(self):
        return self.name


def make_substitute_generics_function(d):
    def substitute(item):
        if isinstance(item, Generic):
            o = d.get(item.name, item)
        else:
            o = symbolic_math.transform(item, substitute)
        return o
    return substitute


def apply_generics(generics, expression):
    substituted = make_substitute_generics_function(generics)(expression)
    value = symbolic_math.get_value(substituted)
    return value


class UnresolvedConstant:

    def __init__(self, name):
        self.name = name

    def value(self):
        raise Exception('Constant {} is not resolved'.format(self.name))

    def str_expression(self):
        return self.name


class Constant:

    def __init__(self, name, expression):
        self.name = name
        self.expression = expression

    def value(self):
        return symbolic_math.get_value(self.expression)

    def str_expression(self):
        return self.name


def resolve_expression(e, constants):
    constant_dependencies = symbolic_math.get_constant_list(e)
    missing_constants = set(constant_dependencies) - set(constants.keys())
    if missing_constants:
        raise Exception('Missing constants {}'.format(missing_constants))
    if constant_dependencies:
        resolved_e = symbolic_math.make_substitute_function(constants)(e)
    else:
        resolved_e = e
    return resolved_e


class StdLogic:

    width = 1
    resolved = True

    def __str__(self):
        return 'std_logic'

    def to_slv(self, data, generics):
        assert(data in (0, 1))
        if data:
            slv = '1'
        else:
            slv = '0'
        return slv

    def from_slv(self, slv, generics):
        mapping = {
            '0': 0,
            '1': 1,
            }
        data = mapping.get(slv, None)
        return data

    def reduce_slv(self, slv, generics):
        return self.from_slv(slv[-1], generics), slv[:-1]


std_logic = StdLogic()


class UnresolvedConstrainedArray:

    resolved = False

    def __init__(self, identifier, size, unconstrained_type_identifier=None,
                 unconstrained_type=None):
        self.identifier = identifier
        assert((unconstrained_type_identifier is None) or (unconstrained_type is None))
        assert(not ((unconstrained_type_identifier is None) and (unconstrained_type is None)))
        self.unconstrained_type = unconstrained_type
        self.unconstrained_type_identifier = unconstrained_type_identifier
        if unconstrained_type_identifier is not None:
            self.type_dependencies = [self.unconstrained_type_identifier]
        else:
            self.type_dependencies = self.unconstrained_type.type_dependencies
        self.size = size

    def resolve(self, types, constants):
        if self.unconstrained_type_identifier is not None:
            unconstrained_type = types.get(self.unconstrained_type_identifier)
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

    resolved = True

    def __init__(self, identifier, unconstrained_type, size, constants):
        self.identifier = identifier
        self.unconstrained_type = unconstrained_type
        self.size = size
        self.width = symbolic_math.Multiplication(
            powers=(symbolic_math.Power(number=1, expression=self.size),
                    symbolic_math.Power(number=1, expression=self.unconstrained_type.subtype.width),
                    ))

    def __str__(self):
        s = '{}({}-1 downto 0)'.format(
            self.unconstrained_type.identifier, symbolic_math.str_expression(self.size))
        return s

    def to_slv(self, data, generics):
        size = apply_generics(generics, self.size)
        assert(len(data) == size)
        slv = self.unconstrained_type.to_slv(data, generics)
        return slv

    def reduce_slv(self, slv, generics):
        width = int(apply_generics(generics, self.width))
        these_slv = slv[-width:]
        reduced_slv = slv[:-width]
        data = self.from_slv(these_slv, generics)
        return data, reduced_slv

    def from_slv(self, slv, generics):
        data = self.unconstrained_type.from_slv(slv, generics)
        size = apply_generics(generics, self.size)
        assert(len(data) == size)
        return data


class UnresolvedArray:

    resolved = False

    def __init__(self, identifier, subtype_identifier):
        self.identifier = identifier
        self.subtype_identifier = subtype_identifier
        self.type_dependencies = [self.subtype_identifier]

    def resolve(self, types, constants):
        subtype = types.get(self.subtype_identifier)
        return Array(
            identifier=self.identifier,
            subtype=subtype,
            )


class Array:

    resolved = True

    def __init__(self, identifier, subtype):
        self.identifier = identifier
        self.subtype = subtype

    def to_slv(self, data, generics):
        slv = ''.join([self.subtype.to_slv(d, generics) for d in data])
        return slv

    def from_slv(self, slv, generics):
        w = apply_generics(generics, self.subtype.width)
        intw = int(w)
        assert(intw == w)
        assert(len(slv) % intw == 0)
        n = len(slv)//intw
        assert(n * intw == len(slv))
        slv_pieces = [slv[i*intw: (i+1)*intw] for i in range(n)]
        data = [self.subtype.from_slv(piece, generics) for piece in slv_pieces]
        return data


class StdLogicVector(Array):

    def __init__(self):
        Array.__init__(self, identifier='std_logic_vector', subtype=std_logic)


class UnresolvedConstrainedStdLogicVector(StdLogicVector):

    resolved = False
    type_dependencies = tuple()

    def __init__(self, identifier, size):
        self.identifier = identifier
        self.size = size
        self.width = size

    def resolve(self, types, constants):
        size = resolve_expression(self.size, constants)
        return ConstrainedStdLogicVector(
            identifier=self.identifier, size=size)


class ConstrainedStdLogicVector:

    unconstrained_name = 'std_logic_vector'

    def __init__(self, identifier, size):
        self.identifier = identifier
        self.size = size
        self.width = size

    def __str__(self):
        if self.identifier is None:
            s = '{}({}-1 downto 0)'.format(
                self.unconstrained_name,
                symbolic_math.str_expression(self.size))
        else:
            s = self.identifier
        return s

    def to_slv(self, data, generics):
        size = int(apply_generics(generics, self.size))
        min_value = 0
        max_value = pow(2, size)-1
        assert(data >= min_value)
        assert(data <= max_value)
        bits = []
        for i in range(size):
            bits.append(data % 2)
            data = data >> 1
        assert(data == 0)
        slv = ''.join([std_logic.to_slv(b, generics) for b in reversed(bits)])
        return slv

    def reduce_slv(self, slv, generics):
        width = int(apply_generics(generics, self.width))
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


class Integer():
    '''
    Just at place holder.
    Not implemented yet.
    '''


class Unsigned(StdLogicVector):

    def __init__(self):
        Array.__init__(self, identifier='unsigned', subtype=std_logic)


class UnresolvedConstrainedUnsigned(UnresolvedConstrainedStdLogicVector):

    def resolve(self, types, constants):
        size = resolve_expression(self.size, constants)
        return ConstrainedUnsigned(
            identifier=self.identifier, size=size)


class ConstrainedUnsigned(ConstrainedStdLogicVector):

    unconstrained_name = 'unsigned'


class UnresolvedConstrainedInteger:

    resolved = False
    type_dependencies = tuple()

    def __init__(self, identifier, lower, upper):
        self.identifier = identifier
        self.lower = lower
        self.upper = upper

    def resolve(self, types, constants):
        upper = resolve_expression(self.upper, constants)
        lower = resolve_expression(self.lower, constants)
        return ConstrainedInteger(
            identifier=self.identifier, upper=upper, lower=lower)


class ConstrainedInteger:

    unconstrained_name = 'integer'

    def __init__(self, identifier, upper, lower):
        self.identifier = identifier
        self.upper = upper
        self.lower = lower
        self.width = symbolic_math.Function(
            name='logceil',
            argument=symbolic_math.Addition(
                terms=[symbolic_math.Term(number=1, expression=upper),
                       symbolic_math.Term(number=1, expression=1),
                       symbolic_math.Term(number=-1, expression=lower),
                       ])
            )


class Signed(StdLogicVector):

    def __init__(self):
        Array.__init__(self, identifier='signed', subtype=std_logic)


class UnresolvedConstrainedSigned(UnresolvedConstrainedStdLogicVector):

    def resolve(self, types, constants):
        size = resolve_expression(self.size, constants)
        return ConstrainedSigned(
            identifier=self.identifier, size=size)


class ConstrainedSigned(ConstrainedStdLogicVector):

    resolved = True
    unconstrained_name = 'signed'

    def __init__(self, size):
        Signed.__init__(self)
        self.size = size
        self.max_value = pow(2, size.value()-1)-1
        self.min_value = -pow(2, size.value()-1)

    def to_slv(self, data, generics):
        assert(data >= self.min_value)
        assert(data <= self.max_value)
        size = apply_generics(generics, self.size)
        if data < 0:
            data += pow(2, size)
        slv = ConstrainedUnsigned.to_slv(self, data, generics)
        return slv

    def from_slv(self, slv, generics):
        size = apply_generics(generics, self.size)
        data = ConstrainedUnsigned.from_slv(self, slv, generics)
        if data > self.max_value:
            data -= pow(2, size)
        assert(data >= self.min_value)
        assert(data <= self.max_value)
        return data


def type_width_constant(typ):
    if isinstance(typ, StdLogic):
        width = '1'
    elif isinstance(typ, ConstrainedStdLogicVector):
        width = typ.size
    elif isinstance(typ, ConstrainedArray):
        width = symbolic_math.Multiplication(
            [typ.unconstrained_type.identifier, typ.size], [])
    else:
        width = '{}_width'.format(typ.identifier)
    return width


class UnresolvedRecord:

    resolved = False

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

    resolved = True

    def __init__(self, identifier, names_and_subtypes):
        self.identifier = identifier
        self.names_and_subtypes = names_and_subtypes
        subtype_widths = [subtype.width for name, subtype in names_and_subtypes]
        self.width = symbolic_math.simplify(symbolic_math.Addition([
            symbolic_math.Term(number=1, expression=e) for e in subtype_widths]))

    def __str__(self):
        return self.identifier

    def to_slv(self, data, generics):
        slvs = [
            subtype.to_slv(data[name], generics) for name, subtype in self.names_and_subtypes]
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
        assert(reduced_slv == '')
        return data

    def declaration(self):
        lines = ['type {} is'.format(self.identifier)]
        lines += ['record']
        for name, subtype in self.names_and_subtypes:
            lines += ['    {}: {};'.format(name, subtype)]
        lines += ['end record;']
        return '\n'.join(lines)
