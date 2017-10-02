import logging

from slvcodec import symbolic_math, typs, typ_parser, vhdl_parser


logger = logging.getLogger(__name__)

standard_packages = ('std_logic_1164', 'numeric_std', 'math_real', 'textio')

vparser = vhdl_parser.VHDLParser(None)

def get_types(p):
    types = (
        p.enumeration_types +
        p.record_types +
        p.array_types +
        p.subtypes
        )
    return types


def parsed_from_filename(filename):
    '''
    Parse the contents of a VHDL file using the VUnit VHDL parser.
    '''
    parsed = vparser.parse(filename)
    return parsed


class Use:
    '''
    Defines a package dependency for a package or entity.
    '''
    def __init__(self, library, design_unit, name_within, package=None):
        self.library = library
        self.design_unit = design_unit
        self.name_within = name_within
        self.package = package


def get_parsed_package_dependencies(parsed):
    '''
    Process the 'use' clauses in a parsed file to get a list of the package dependencies.
    '''
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
    '''
    Process the 'use' clauses in a parsed file to get a list of the package dependencies.
    '''
    p_constants = parsed_package.packages[0].constants
    p_types = get_types(parsed_package.packages[0])
    constants = {}
    for c in p_constants:
        if c.text == '':
            # This typically happens when a parameters file has been generated
            # incorrectly.
            raise Exception('Constant {} has no value to parse'.format(c.identifier))
        constants[c.identifier] = symbolic_math.parse_and_simplify(c.text)
    processed_types = [(t.identifier, typ_parser.process_parsed_type(t))
                  for t in p_types]
    # Filter out the types that could not be processed.
    types = dict([(k, v) for k, v in processed_types if v is not None]) 
    failed_type_keys = [k for k, v in processed_types if v is None]
    if failed_type_keys:
        logger.warning('Failed to parse types {}'.format(failed_type_keys))
    uses = get_parsed_package_dependencies(parsed_package)
    p = UnresolvedPackage(
        identifier=parsed_package.packages[0].identifier,
        types=types,
        constants=constants,
        uses=uses,
    )
    return p


def resolve_packages(packages):
    '''
    Takes at list of packages and resolves their references
    to one another.
    Returns a dictionary of resolved packages.
    '''
    pd = dict([(p.identifier, p) for p in packages])
    resolved_pd = {
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
    resolved_package_names = list(standard_packages)
    toresolve_package_names = [p.identifier for p in packages]
    while toresolve_package_names:
        any_resolved = False
        for pn in toresolve_package_names:
            dependencies = pd[pn].uses.keys()
            if not (set(dependencies) - set(resolved_package_names)):
                resolved = pd[pn].resolve(resolved_pd)
                any_resolved = True
                resolved_package_names.append(pn)
                resolved_pd[pn] = resolved
            else:
                logger.debug('Trying to resolve {} but has unresolved dependencies {}'.format(pn, set(dependencies) - set(resolved_package_names)))
        toresolve_package_names = [x for x in toresolve_package_names
                                   if x not in resolved_package_names]
        if not any_resolved:
            raise Exception('Failing to resolve packages {}'.format(
                toresolve_package_names))
    return resolved_pd


def parse_process_and_resolve_packages(filenames):
    parsed = [parsed_from_filename(fn) for fn in filenames]
    processed = [process_parsed_package(p) for p in parsed]
    resolved_packages = resolve_packages(processed)
    return resolved_packages


def exclusive_dict_merge(a, b):
    '''
    Merges two dictionaries confirming that their are no
    keys present in both dictionaries.
    '''
    assert(not (set(a.keys()) & set(b.keys())))
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


def resolve_dependencies(available, unresolved, dependencies, resolve_function):
    '''
    Resolves dependencies.

    Args:
      `available`: a dictionary of already resolved items.
      `unresolved`: a dictionary of items that have not been resolved.
      `dependencies`: the items upon which each unresolved item is dependent.
      `resolve_function`: a function that resolves an item with arguments
           (unresolved_name, unresolved_item, dictionary_of_resolved_items)

    Returns:
      `resolved`: a dictionary of resolved item.
    '''
    updated_available = available.copy()
    unresolved_names = list(unresolved.keys())
    available_names = list(available.keys())
    assert(not (set(unresolved_names) & set(available_names)))
    resolved = {}
    failed = {}
    failed_names = []
    while unresolved_names:
        any_changes = False
        for unresolved_name in unresolved_names:
            unresolved_item = unresolved[unresolved_name]
            item_dependencies = dependencies[unresolved_name]
            if set(item_dependencies) & set(failed_names):
                any_changes = True
                # Cannot resolve this since a dependency has failed.
                failed[unresolved_name] = unresolved_item
                failed_names.append(unresolved_name)
            elif not (set(item_dependencies) - set(available_names)):
                any_changes = True
                failed_to_resolve = False
                resolved_item = resolve_function(
                    unresolved_name, unresolved_item, updated_available)
                try:
                    resolved_item = resolve_function(
                        unresolved_name, unresolved_item, updated_available)
                except Exception as e:
                    logger.error('Failed to resolve {}.  Error caught when resolving.'.format(unresolved_name))
                    failed[unresolved_name] = unresolved_item
                    failed_names.append(unresolved_name)
                    failed_to_resolve = True
                if not failed_to_resolve:
                    assert(unresolved_name not in resolved)
                    resolved[unresolved_name] = resolved_item
                    assert(unresolved_name not in updated_available)
                    updated_available[unresolved_name] = resolved_item
                    assert(unresolved_name not in available_names)
                    available_names.append(unresolved_name)
        if not any_changes:
            logger.debug('Failed to resolve {}'.format(unresolved_names))
            for unresolved_name in unresolved_names:
                unresolved_item = unresolved[unresolved_name]
                logger.debug('{} was missing the dependencies: {}'.format(
                    unresolved_name,
                    set(dependencies[unresolved_name]) - set(available_names)))
                failed[unresolved_name] = unresolved_item
                failed_names.append(unresolved_name)
        unresolved_names = list(set(unresolved_names) - set(available_names) -
                                set(failed_names))
    return resolved, failed


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
            resolved = symbolic_math.make_substitute_function(
                resolved_constants)(constant)
            resolved_constant = typs.Constant(name=name, expression=resolved)
            return resolved_constant

        constant_dependencies = dict([
            (name, symbolic_math.get_constant_list(c))
            for name, c in self.constants.items()])
        resolved_constants, failed_constants = resolve_dependencies(
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
        resolved_types, failed_types = resolve_dependencies(
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
