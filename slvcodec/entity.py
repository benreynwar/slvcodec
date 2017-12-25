import collections
import logging

from slvcodec import package, math_parser, typs, resolution


logger = logging.getLogger(__name__)


# Port names that will be recognized as clocks.
CLOCK_NAMES = ('clk', 'clock')


class Port:
    '''
    A resolved or unresolved entity port.
    '''

    def __init__(self, name, direction, typ):
        self.name = name
        if direction is None:
            # Default direction is 'in'.
            direction = 'in'
        self.direction = direction
        self.typ = typ


class UnresolvedEntity:
    '''
    Keeps track of the generics, ports and package dependencies of
    an entity.
    '''

    def __init__(self, identifier, generics, ports, uses):
        self.identifier = identifier
        self.generics = generics
        self.ports = ports
        self.uses = uses

    def resolve_port(self, port, available_types, available_constants):
        '''
        Resolve a port of the entity.

        `port`: The unresolved port object.
        `available_types`: A dictionary of known types.
        `available_constants`: A dictionary of known constants and generics.
        '''
        if port.typ in available_types:
            resolved_typ = available_types[port.typ]
        elif isinstance(port.typ, str):
            raise resolution.ResolutionError(
                'Failed to resolve port of type "{}".  '.format(port.type) +
                'Perhaps a use statement is missing.')
        else:
            resolved_typ = port.typ.resolve(
                available_types, available_constants)
        resolved_port = Port(name=port.name, direction=port.direction,
                             typ=resolved_typ)
        if resolved_port.typ.unconstrained:
            raise resolution.ResolutionError('Entity {}: Port {}: unconstrained port'.format(
                self.identifier, port.name))
        return resolved_port

    def resolve(self, packages, must_resolve=True):
        '''
        Resolve the entity.

        This involves resolving the uses, constants and ports.
        '''
        resolved_uses = package.resolve_uses(
            self.uses, packages, must_resolve=must_resolve)
        available_types, available_constants = package.combine_packages(
            [u.package for u in resolved_uses.values()])
        available_constants_generics = package.exclusive_dict_merge(
            available_constants, self.generics)
        resolved_ports = collections.OrderedDict()
        for name, port in self.ports.items():
            try:
                resolved_port = self.resolve_port(
                    port=port,
                    available_types=available_types,
                    available_constants=available_constants_generics)
                resolved_ports[name] = resolved_port
            except resolution.ResolutionError as error:
                # If we can't resolve and `must_resolve` isn't True then we just
                # skip ports that we can't resolve.
                if must_resolve:
                    error_msg = 'Failed to resolve port {} in entity {}.'.format(
                        self.identifier, port.name)
                    error_msg += '  ' + error.args[0]
                    raise resolution.ResolutionError(error_msg) from error
        resolved_entity = Entity(
            identifier=self.identifier,
            generics=self.generics,
            ports=resolved_ports,
            uses=resolved_uses,
        )
        return resolved_entity


class Entity(object):
    '''
    An entity with all types and constants in the ports resolved.
    '''

    resolved = True

    def __init__(self, identifier, generics, ports, uses):
        self.identifier = identifier
        self.generics = generics
        self.ports = ports
        self.uses = uses

    def __str__(self):
        return 'Entity({})'.format(self.identifier)

    def __repr__(self):
        return str(self)

    def input_ports(self):
        '''
        Get an ordered dictionary of the input ports.
        '''
        input_ports = collections.OrderedDict([
            (port_name, port) for port_name, port in self.ports.items()
            if (port.direction == 'in') and (port.name not in CLOCK_NAMES)])
        return input_ports

    def inputs_to_slv(self, inputs, generics):
        '''
        Takes a dictionary of inputs, and a dictionary of generics parameters for the entity
        and produces a string of '0's and '1's representing the input values.
        '''
        slvs = []
        for port in self.input_ports().values():
            port_inputs = inputs.get(port.name, None)
            try:
                port_slv = port.typ.to_slv(port_inputs, generics)
            except typs.ToSlvError as error:
                message = 'Failure to convert inputs to binary for entity {} and port {}.'.format(
                    self.identifier, port.name)
                message += '  ' + error.args[0]
                raise typs.ToSlvError(message) from error
            slvs.append(port_slv)
        invalid_input_names = set(inputs.keys()) - set(self.input_ports().keys())
        if invalid_input_names:
            raise typs.ToSlvError(
                'In entity {} values given for port that does not exist: {}'.format(
                    self.identifier, invalid_input_names))
        slv = ''.join(reversed(slvs))
        return slv

    def ports_from_slv(self, slv, generics, direction):
        '''
        Extract port values from an slv string.

        'slv': A string of 0's and 1's representing the port data.
        'generics': The generic parameters for the entity.
        'directrion': Whether we are extracting input or output ports.
        '''
        assert direction in ('in', 'out')
        pos = 0
        outputs = {}
        for port in self.ports.values():
            if (port.direction == direction) and (port.name not in CLOCK_NAMES):
                width_symbol = typs.make_substitute_generics_function(generics)(port.typ.width)
                width = math_parser.get_value(width_symbol)
                intwidth = int(width)
                assert width == intwidth
                if pos == 0:
                    piece = slv[-intwidth:]
                else:
                    piece = slv[-pos-intwidth: -pos]
                pos += intwidth
                port_value = port.typ.from_slv(piece, generics)
                outputs[port.name] = port_value
        return outputs

    def outputs_from_slv(self, slv, generics):
        '''
        Extract output port values from a string of 0's and 1's.
        '''
        slv = slv.strip()
        data = self.ports_from_slv(slv, generics, 'out')
        return data

    def inputs_from_slv(self, slv, generics):
        '''
        Extract input port values from a string of 0's and 1's.
        '''
        slv = slv.strip()
        data = self.ports_from_slv(slv, generics, 'in')
        return data
