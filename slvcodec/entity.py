import collections
import logging

from slvcodec import package, typ_parser, symbolic_math, typs, errors


logger = logging.getLogger(__name__)

CLOCK_NAMES = ('clk', 'clock')


def process_files(filenames, must_resolve=True):
    '''
    Takes a list of filenames,
    parses them with the VUnit parser
    and then processes them in slvcodec classes.

    The packages references to one another are resolved as
    are the references to types and constants in the entity
    interfaces.
    '''
    entities = {}
    packages = []
    for filename in filenames:
        parsed = package.parsed_from_filename(filename)
        if parsed.entities:
            assert(len(parsed.entities) == 1)
            p = process_parsed_entity(parsed)
            entities[p.identifier] = p
            assert(not parsed.packages)
        if parsed.packages:
            pkg = package.process_parsed_package(parsed)
            packages.append(pkg)
    resolved_packages = package.resolve_packages(packages)
    resolved_entities = dict([(e.identifier, e.resolve(resolved_packages, must_resolve=must_resolve))
                             for e in entities.values()])
    return resolved_entities, resolved_packages


def process_parsed_entity(parsed_entity):
    '''
    Processes the parse entity (output from VUnit vhdl_parser)
    into an UnresolvedEntity class.
    '''
    p_generics = parsed_entity.entities[0].generics
    generics = [typs.Generic(
        name=g.identifier,
        typ=typ_parser.process_subtype_indication(g.subtype_indication),
        ) for g in p_generics]
    p_ports = parsed_entity.entities[0].ports
    ports = [Port(
        name=p.identifier,
        direction=p.mode,
        typ=typ_parser.process_subtype_indication(p.subtype_indication),
        ) for p in p_ports]
    gd = dict([(g.name, g) for g in generics])
    pd = collections.OrderedDict([(p.name, p) for p in ports])
    uses = package.get_parsed_package_dependencies(parsed_entity)
    p = UnresolvedEntity(
        identifier=parsed_entity.entities[0].identifier,
        generics=gd,
        ports=pd,
        uses=uses,
    )
    return p


class Port:

    def __init__(self, name, direction, typ):
        self.name = name
        if direction == None:
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

    def resolve(self, packages, must_resolve=True):
        resolved_uses = package.resolve_uses(self.uses, packages, must_resolve=must_resolve)
        available_types, available_constants = package.combine_packages(
            [u.package for u in resolved_uses.values()])
        available_constants = package.exclusive_dict_merge(
            available_constants, self.generics)
        resolved_ports = collections.OrderedDict()
        for name, port in self.ports.items():
            try:
                if port.typ in available_types:
                    resolved_typ = available_types[port.typ]
                elif isinstance(port.typ, str):
                    raise errors.ResolutionError('Failed to resolve port of type "{}".  Perhaps a use statement is missing.'.format(port.typ))
                else:
                    resolved_typ = port.typ.resolve(available_types, available_constants)
                resolved_port = Port(name=port.name, direction=port.direction,
                                    typ=resolved_typ)
                if resolved_port.typ.unconstrained:
                    raise errors.ResolutionError('Entity {}: Port {}: unconstrained port'.format(
                        self.identifier, port.name))
                resolved_ports[name] = resolved_port
            except errors.ResolutionError as e:
                # If we can't resolve and `must_resolve` isn't True then we just
                # skip ports that we can't resolve.
                if must_resolve:
                    error_msg = 'Failed to resolve port {} in entity {}.'.format(
                        self.identifier, port.name)
                    error_msg += '  ' + e.args[0]
                    raise errors.ResolutionError(error_msg) from e
        e = Entity(
            identifier=self.identifier,
            generics=self.generics,
            ports=resolved_ports,
            uses=resolved_uses,
        )
        return e


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
        input_ports = dict([
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
            d = inputs.get(port.name, None)
            try:
                o = port.typ.to_slv(d, generics)
            except typs.ToSlvError as e:
                message = 'Failure to convert inputs to binary for entity {} and port {}.'.format(
                    self.identifier, port.name)
                message += '  ' + e.args[0]
                raise typs.ToSlvError(message) from e
            slvs.append(o)
        invalid_input_names = set(inputs.keys()) - set(self.input_ports().keys())
        if invalid_input_names:
            raise typs.ToSlvError('In entity {} values given for port that does not exist: {}'.format(
                self.identifier, invalid_input_names))
        slv = ''.join(reversed(slvs))
        return slv

    def ports_from_slv(self, slv, generics, direction):
        pos = 0
        outputs = {}
        for port in self.ports.values():
            if (port.direction == direction) and (port.name not in CLOCK_NAMES):
                w = typs.make_substitute_generics_function(generics)(port.typ.width)
                width = symbolic_math.get_value(w)
                intwidth = int(width)
                assert(width == intwidth)
                if pos == 0:
                    piece = slv[-intwidth:]
                else:
                    piece = slv[-pos-intwidth: -pos]
                pos += intwidth
                o = port.typ.from_slv(piece, generics)
                outputs[port.name] = o
        return outputs

    def outputs_from_slv(self, slv, generics):
        slv = slv.strip()
        data = self.ports_from_slv(slv, generics, 'out')
        return data

    def inputs_from_slv(self, slv, generics):
        slv = slv.strip()
        data = self.ports_from_slv(slv, generics, 'in')
        return data
