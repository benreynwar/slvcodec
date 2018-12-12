import logging

from slvcodec import math_parser, typs, typ_parser, dependencies


logger = logging.getLogger(__name__)

STANDARD_PACKAGES = ('std_logic_1164', 'numeric_std', 'math_real', 'textio')


class Use:
    '''
    Defines a package dependency for a package or entity.
    '''
    def __init__(self, library, design_unit, name_within, package=None):
        self.library = library
        self.design_unit = design_unit
        self.name_within = name_within
        self.package = package


class Package(object):
    '''
    A package defines all the types, constants and dependencies of that package.
    The dependencies of the types and constants on other packages have
    been resolved.
    '''

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


BUILTIN_PACKAGES = {
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
    'textio': Package(
        identifier='textio', constants={}, types={
        }, uses={}),
}


def resolve_packages(packages):
    '''
    Takes at list of packages and resolves their references
    to one another.
    Returns a dictionary of resolved packages.
    '''
    package_dict = dict([(p.identifier, p) for p in packages])
    resolved_pd = BUILTIN_PACKAGES.copy()
    resolved_package_names = list(STANDARD_PACKAGES)
    toresolve_package_names = [p.identifier for p in packages]
    while toresolve_package_names:
        any_resolved = False
        for pn in toresolve_package_names:
            dependencies = package_dict[pn].uses.keys()
            if not (set(dependencies) - set(resolved_package_names)):
                resolved = package_dict[pn].resolve(resolved_pd)
                any_resolved = True
                resolved_package_names.append(pn)
                resolved_pd[pn] = resolved
            else:
                logger.debug('Trying to resolve %s but has unresolved dependencies %s',
                             pn, set(dependencies) - set(resolved_package_names))
        toresolve_package_names = [x for x in toresolve_package_names
                                   if x not in resolved_package_names]
        if not any_resolved:
            raise Exception('Failing to resolve packages {}'.format(
                toresolve_package_names))
    return resolved_pd


def exclusive_dict_merge(a, b):
    '''
    Merges two dictionaries confirming that their are no
    keys present in both dictionaries.
    '''
    assert not (set(a.keys()) & set(b.keys()))
    c = a.copy()
    c.update(b)
    return c


def combine_packages(packages):
    '''
    Retrieve a dictionary of types and a dictionary of constants from a list of
    packages.
    '''
    combined_types = {}
    combined_constants = {}
    for p in packages:
        combined_types = exclusive_dict_merge(combined_types, p.types)
        combined_constants = exclusive_dict_merge(combined_constants, p.constants)
    return combined_types, combined_constants


def resolve_uses(uses, packages, must_resolve=True):
    '''
    Resolves a list of uses.
    Returns a list of resolved uses contain a direct
    reference to the appropriate package.
    '''
    resolved_uses = {}
    for use_name, use in uses.items():
        if use_name not in packages:
            if must_resolve:
                raise Exception('Did not find dependency package {}'.format(use_name))
        elif not packages[use_name].resolved:
            if must_resolve:
                raise Exception('Dependency package {} is not resolved'.format(use_name))
        else:
            resolved_uses[use_name] = Use(
                library=use.library,
                design_unit=use.design_unit,
                name_within=use.name_within,
                package=packages[use_name],
            )
    return resolved_uses


class UnresolvedPackage:
    '''
    A package defines all the types, constants and dependencies of that package.
    The dependencies of the types and constants on other packages have
    not yet been resolved.
    '''

    def __init__(self, identifier, types, constants, uses):
        self.identifier = identifier
        self.types = types
        self.constants = constants
        self.uses = uses

    def resolve(self, packages):
        resolved_uses = resolve_uses(self.uses, packages)
        available_types, available_constants = combine_packages(
            [u.package for u in resolved_uses.values()])

        def resolve_constant(name, constant, resolved_constants):
            resolved = math_parser.make_substitute_function(
                resolved_constants)(constant)
            resolved_constant = typs.Constant(name=name, expression=resolved)
            return resolved_constant

        constant_dependencies = dict([
            (name, math_parser.get_constant_list(c))
            for name, c in self.constants.items()])
        resolved_constants, failed_constants = dependencies.resolve_dependencies(
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
        resolved_types, failed_types = dependencies.resolve_dependencies(
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
