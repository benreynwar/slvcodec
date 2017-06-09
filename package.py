import logging

from slvcodec import symbolic_math, typs, typ_parser, config
from vunit import vhdl_parser

logger = logging.getLogger(__name__)

standard_packages = ('standard', 'std_logic_1164', 'numeric_std', 'math_real')


def parsed_package_from_filename(filename):
    with open(filename, 'r') as f:
        code = f.read()
    parsed = vhdl_parser.VHDLParser.parse(code, None)
    return parsed


class Use:

    def __init__(self, library, design_unit, name_within, package=None):
        self.library = library
        self.design_unit = design_unit
        self.name_within = name_within
        self.package = package


def get_parsed_package_dependencies(parsed):
    uses = {}
    for reference in parsed.references:
        if reference.is_package_reference():
            if reference.design_unit in uses:
                raise Exception('Two packages with same name.')
            if reference.name_within != 'all':
                raise Exception("Can't deal with use statements that don't use 'all'")
            uses[reference.design_unit] = Use(
                library=reference.library, design_unit=reference.design_unit,
                name_within=reference.name_within)
    return uses


def process_parsed_package(parsed_package):
    p_constants = parsed_package.packages[0].constants
    p_types = parsed_package.packages[0].types
    constants = dict([(c.identifier, symbolic_math.parse_and_simplify(c.text))
                      for c in p_constants])
    types = dict([(t.identifier, typ_parser.process_parsed_type(t))
                  for t in p_types])
    uses = get_parsed_package_dependencies(parsed_package)
    p = UnresolvedPackage(
        identifier=parsed_package.packages[0].identifier,
        types=types,
        constants=constants,
        uses=uses,
    )
    return p


def process_packages(filenames):
    parsed_packages = [parsed_package_from_filename(fn) for fn in filenames]
    processed_packages = [process_parsed_package(p) for p in parsed_packages]
    resolved_pd = resolve_packages(processed_packages)
    return resolved_pd


def resolve_packages(packages):
    pd = dict([(p.identifier, p) for p in packages])
    resolved_pd = {
        'standard': Package(
            identifier='standard', constants={}, types={
                'integer': typs.Integer(),
                }, uses={}),
        'std_logic_1164': Package(
            identifier='std_logic_1164', constants={}, types={
                'std_logic_vector': typs.StdLogicVector(),
                'std_logic': typs.std_logic,
                }, uses={}),
        'numeric_std': Package(
            identifier='numeric_std', constants={}, types={
                'unsigned': typs.Unsigned(),
                'signed': typs.Signed(),
                }, uses={}),
        'math_real': Package(
            identifier='math_real', constants={}, types={
                }, uses={}),
        }
    resolved_package_names = list(standard_packages)
    toresolve_package_names = [p.identifier for p in packages]
    while toresolve_package_names:
        any_resolved = False
        for pn in toresolve_package_names:
            dependencies = pd[pn].uses.keys()
            logger.debug('dependencies are {}'.format(dependencies))
            logger.debug('resolved are {}'.format(resolved_package_names))
            if not (set(dependencies) - set(resolved_package_names)):
                resolved = pd[pn].resolve(resolved_pd)
                any_resolved = True
                resolved_package_names.append(pn)
                resolved_pd[pn] = resolved
        toresolve_package_names = [x for x in toresolve_package_names
                                   if x not in resolved_package_names]
        if not any_resolved:
            raise Exception('Failing to resolve packages {}'.format(
                toresolve_package_names))
    return resolved_pd


def exclusive_dict_merge(a, b):
    assert(not (set(a.keys()) & set(b.keys())))
    c = a.copy()
    c.update(b)
    return c


def combine_packages(packages):
    combined_types = {}
    combined_constants = {}
    for p in packages:
        combined_types = exclusive_dict_merge(combined_types, p.types)
        combined_constants = exclusive_dict_merge(combined_constants, p.constants)
    return combined_types, combined_constants


def resolve_dependencies(available, unresolved, dependencies, resolve_function):
    updated_available = available.copy()
    unresolved_names = list(unresolved.keys())
    available_names = list(available.keys())
    assert(not set(unresolved_names) & set(available_names))
    resolved = {}
    while unresolved_names:
        any_resolved = False
        for unresolved_name in unresolved_names:
            unresolved_item = unresolved[unresolved_name]
            item_dependencies = dependencies[unresolved_name]
            if not (set(item_dependencies) - set(available_names)):
                any_resolved = True
                resolved_item = resolve_function(
                    unresolved_name, unresolved_item, updated_available)
                assert(unresolved_name not in resolved)
                resolved[unresolved_name] = resolved_item
                assert(unresolved_name not in updated_available)
                updated_available[unresolved_name] = resolved_item
                assert(unresolved_name not in available_names)
                available_names.append(unresolved_name)
        unresolved_names = list(set(unresolved_names) - set(available_names))
        if not any_resolved:
            raise Exception('Failed to resolve {}'.format(unresolved_names))
    return resolved


def resolve_uses(uses, packages):
    resolved_uses = {}
    for use_name, use in uses.items():
        if use_name not in packages:
            raise Exception('Did not find dependency package {}'.format(use_name))
        if not packages[use_name].resolved:
            raise Exception('Dependency package {} is not resolved'.format(use_name))
        resolved_uses[use_name] = Use(
            library=use.library,
            design_unit=use.design_unit,
            name_within=use.name_within,
            package=packages[use_name],
            )
    return resolved_uses


class UnresolvedPackage:

    def __init__(self, identifier, types, constants, uses):
        self.identifier = identifier
        self.types = types
        self.constants = constants
        self.uses = uses

    def resolve(self, packages):
        resolved_uses = resolve_uses(self.uses, packages)
        available_types, available_constants = combine_packages(
            [u.package for u in resolved_uses.values()] + [packages['standard']])

        def resolve_constant(name, constant, resolved_constants):
            resolved = symbolic_math.make_substitute_function(
                available_constants)(constant)
            resolved_constant = typs.Constant(name=name, expression=resolved)
            return resolved_constant

        constant_dependencies = dict([
            (name, symbolic_math.get_constant_list(c))
            for name, c in self.constants.items()])
        resolved_constants = resolve_dependencies(
            available=available_constants,
            unresolved=self.constants,
            dependencies=constant_dependencies,
            resolve_function=resolve_constant,
            )

        available_constants.update(resolved_constants)

        def resolve_type(name, typ, resolved_types):
            resolved = typ.resolve(resolved_types, available_constants)
            return resolved

        type_dependencies = dict([
            (name, t.type_dependencies) for name, t in self.types.items()])
        resolved_types = resolve_dependencies(
            available=available_types,
            unresolved=self.types,
            dependencies=type_dependencies,
            resolve_function=resolve_type,
            )

        p = Package(
            identifier=self.identifier,
            types=resolved_types,
            constants=resolved_constants,
            uses=resolved_uses,
            )
        return p


class Package(object):

    resolved = True

    def __init__(self, identifier, types, constants, uses):
        self.identifier = identifier
        self.types = types
        self.constants = constants
        self.uses = uses

    def __str__(self):
        return 'Package({})'.format(self.identifier)

    def __repr__(self):
        return str(self)


def test_dummy_width():
    packages = process_packages(['tests/vhdl_type_pkg.vhd'])
    p = packages['vhdl_type_pkg']
    t = p.types['t_dummy']
    assert(t.width.value() == 30)


if __name__ == '__main__':
    config.setup_logging(logging.DEBUG)
    test_dummy_width()
