from slvcodec import symbolic_math


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

    def to_slv(self, data):
        assert(data in (0, 1))
        if data:
            slv = '1'
        else:
            slv = '0'
        return slv

    def from_slv(self, slv):
        mapping = {
            '0': 0,
            '1': 1,
            }
        data = mapping[slv]
        return data

    def reduce_slv(self, slv):
        return self.from_slv(slv[0]), slv[1:]

std_logic = StdLogic()


class UnresolvedConstrainedArray:

    resolved = False

    def __init__(self, identifier, unconstrained_type_identifier, size):
        self.identifier = identifier
        self.unconstrained_type_identifier = unconstrained_type_identifier
        self.size = size
        self.type_dependencies = [self.unconstrained_type_identifier]

    def resolve(self, types, constants):
        unconstrained_type = types.get(self.unconstrained_type_identifier)
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
            [self.size, self.unconstrained_type.subtype.width], [])

    def __str__(self):
        s = '{}({}-1 downto 0)'.format(
            self.unconstrained_type.identifier, symbolic_math.str_expression(self.size))
        return s

    def to_slv(self, data):
        assert(len(data) == self.size.value())
        slv = self.unconstrained_type.to_slv(data)
        return slv

    def from_slv(self, slv):
        data = self.unconstrained_type.from_slv(slv)
        assert(len(data) == self.size.value())
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

    def __init__(self, identifier, size):
        self.identifier = identifier
        self.size = size
        self.min_value = 0
        self.max_value = pow(2, self.size.value())-1
        self.width = size

    def __str__(self):
        s = 'std_logic_vector({}-1 downto 0)'.format(
            symbolic_math.str_expression(self.size))
        return s

    def to_slv(self, data):
        assert(data >= self.min_value)
        assert(data <= self.max_value)
        bits = []
        for i in range(self.size.value()):
            bits.append(data % 2)
            data = data >> 1
        assert(data == 0)
        slv = ''.join([std_logic.to_slv(b) for b in bits])
        return slv

    def from_slv(self, slv):
        bits = [std_logic.from_slv(c) for c in slv]
        data = 0
        for b in bits:
            data = (data << 1) + b
        return data


class Unsigned(StdLogicVector):

    resolved = True

    @classmethod
    def constrain(cls, size):
        return ConstrainedUnsigned(size)


class ConstrainedUnsigned(ConstrainedStdLogicVector):

    resolved = True


class Signed(StdLogicVector):

    resolved = True

    @classmethod
    def constrain(cls, size):
        return ConstrainedSigned(size)


class ConstrainedSigned(Signed):

    resolved = True

    def __init__(self, size):
        Signed.__init__(self)
        self.size = size
        self.max_value = pow(2, size.value()-1)-1
        self.min_value = -pow(2, size.value()-1)

    def to_slv(self, data):
        assert(data >= self.min_value)
        assert(data <= self.max_value)
        if data < 0:
            data += pow(2, self.size)
        slv = ConstrainedUnsigned.to_slv(self, data)
        return slv

    def from_slv(self, slv):
        data = ConstrainedUnsigned.from_slv(self, slv)
        if data > self.max_value:
            data -= pow(2, self.size.value())
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

    def to_slv(self, data):
        slvs = [
            subtype.to_slv(data[name]) for name, subtype in self.names_and_subtypes]
        slv = ''.join(slvs)
        return slv

    def reduce_slv(self, slv):
        reduced_slv = slv
        data = {}
        for name, subtype in self.names_and_subtypes:
            data[name], reduced_slv = subtype.reduce_slv(reduced_slv)
        return data, reduced_slv

    def from_slv(self, slv):
        data, reduced_slv = self.reduce_slv(slv)
        assert(reduced_slv == '')
        return data

    def declaration(self):
        lines = ['type {} is'.format(self.identifier)]
        lines += ['record']
        for name, subtype in self.names_and_subtypes:
            lines += ['    {}: {};'.format(name, subtype)]
        lines += ['end record;']
        return '\n'.join(lines)
