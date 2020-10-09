import logging
import collections

from slvcodec import inner_vhdl_parser, package
from slvcodec import math_parser, typ_parser
from slvcodec import entity, typs


logger = logging.getLogger(__name__)

STANDARD_PACKAGES = ('std_logic_1164', 'numeric_std', 'math_real', 'textio')

# Port names that will be recognized as clocks.
CLOCK_NAMES = ('clk', 'clock')


def get_parsed_dependencies(references):
    '''
    Process the 'use' clauses in a parsed file to get a list of the package dependencies.
    '''
    uses = {}
    for reference in references:
        if reference.is_package_reference():
            if reference.design_unit in uses:
                raise Exception('Two packages with same name.')
            if reference.name_within != 'all':
                raise Exception("Can't deal with use statements that don't use 'all'")
            uses[reference.design_unit] = package.Use(
                library=reference.library, design_unit=reference.design_unit,
                name_within=reference.name_within)
    return uses


def get_types(parsed_package):
    '''
    Get a list of all types defined in the parsed package.
    '''
    types = (
        parsed_package.enumeration_types +
        parsed_package.record_types +
        parsed_package.array_types +
        parsed_package.subtypes
    )
    return types


def parse_package_string(code):
    '''
    Parse a string containing a package definition and it's 'use' statements.
    '''
    cleaned_code = inner_vhdl_parser.remove_comments(code.lower())
    parsed_packages = list(inner_vhdl_parser.VHDLPackage.find(cleaned_code))
    parsed_uses = get_parsed_dependencies(inner_vhdl_parser.VHDLReference.find(code.lower()))
    assert len(parsed_packages) == 1
    processed = process_parsed_package(parsed_packages[0], parsed_uses)
    return processed


def process_parsed_package(parsed_package, parsed_uses):
    '''
    Process a parsed package (from inner_vhdl_parser) into an UnresolvedPackage object.
    '''
    p_constants = parsed_package.constants
    p_types = get_types(parsed_package)
    constants = {}
    for constant in p_constants:
        if constant.text == '':
            # This typically happens when a parameters file has been generated
            # incorrectly.
            raise Exception('Constant {} has no value to parse'.format(constant.identifier))
        constants[constant.identifier] = math_parser.parse_and_simplify(constant.text)
    processed_types = [(t.identifier, typ_parser.process_parsed_type(t))
                       for t in p_types]
    # Filter out the types that could not be processed.
    types = dict([(k, v) for k, v in processed_types if v is not None])
    failed_type_keys = [k for k, v in processed_types if v is None]
    if failed_type_keys:
        logger.warning('Failed to parse types %s', str(failed_type_keys))
    processed_package = package.UnresolvedPackage(
        identifier=parsed_package.identifier,
        types=types,
        constants=constants,
        uses=parsed_uses,
    )
    return processed_package


TEST_ENTITY_STRING = '''
library ieee;
use ieee.std_logic_1164.all;

entity simple is
generic (
  FISH: natural
  );
port (
  clk: in std_logic;
  i_valid: in std_logic;
  o_valid: out std_logic
);
end entity;
'''


def parse_entity_string(code):
    '''
    Parse and process code for VHDL entity.

    >>> ent = parse_entity_string(TEST_ENTITY_STRING)
    >>> ent.ports['o_valid'].name
    'o_valid'
    >>> ent.ports['o_valid'].typ
    'std_logic'
    >>> ent.generics['fish'].typ
    'natural'
    '''
    cleaned_code = inner_vhdl_parser.remove_comments(code.lower())
    parsed_entities = list(inner_vhdl_parser.VHDLEntity.find(cleaned_code))
    parsed_uses = get_parsed_dependencies(inner_vhdl_parser.VHDLReference.find(code.lower()))
    assert len(parsed_entities) == 1
    processed = process_parsed_entity(parsed_entities[0], parsed_uses)
    return processed


def clean_identifier(identifier):
    '''
    Strip any comments out of an identifier.
    '''
    lines = identifier.split('\n')
    cleaned = ''
    for line in lines:
        index = line.find('--')
        if index >= 0:
            line = line[:index]
        cleaned += line.strip()
    return cleaned


def process_parsed_entity(parsed_entity, parsed_uses):
    '''
    Processes the parse entity (output from VUnit inner_vhdl_parser)
    into an UnresolvedEntity class.
    '''
    p_generics = parsed_entity.generics
    generics = [typs.Generic(
        name=g.identifier,
        typ=typ_parser.process_subtype_indication(g.subtype_indication),
        ) for g in p_generics]
    p_ports = parsed_entity.ports
    ports = [entity.Port(
        name=clean_identifier(p.identifier),
        direction=p.mode,
        typ=typ_parser.process_subtype_indication(p.subtype_indication),
        ) for p in p_ports]
    generics_dict = dict([(g.name, g) for g in generics])
    ports_dict = collections.OrderedDict([(p.name, p) for p in ports])
    processed_entity = entity.UnresolvedEntity(
        identifier=parsed_entity.identifier,
        generics=generics_dict,
        ports=ports_dict,
        uses=parsed_uses,
    )
    return processed_entity


def extract_references(code):
    '''
    Extract of list of strings for 'use' clauses and other references
    from a string.
    '''
    patterns = (
        inner_vhdl_parser.VHDLReference._uses_re,
        inner_vhdl_parser.VHDLReference._entity_reference_re,
        inner_vhdl_parser.VHDLReference._configuration_reference_re,
        inner_vhdl_parser.VHDLReference._package_instance_re,
    )
    reference_codes = []
    for pattern in patterns:
        for match in pattern.finditer(code):
            reference_codes.append(match.string)
    return reference_codes


def extract_entities(code):
    entity_codes = list(inner_vhdl_parser.VHDLEntity.find_code(code))
    return entity_codes


def extract_packages(code):
    package_codes = list(inner_vhdl_parser.VHDLPackage.find_code(code))
    return package_codes


def parse_string(code):
    '''
    Parse entity and package objects from a string.
    '''
    first_entities = list(inner_vhdl_parser.VHDLEntity.find(code))
    first_packages = list(inner_vhdl_parser.VHDLPackage.find(code))
    if first_entities:
        parsed_entities = [parse_entity_string(code)]
    else:
        parsed_entities = []
    if first_packages:
        parsed_packages = [parse_package_string(code)]
    else:
        parsed_packages = []
    return parsed_entities, parsed_packages


def parse_file(filename):
    '''
    Parse entity and package objects from a file.
    '''
    with open(filename, 'r') as f:
        code = f.read()
    parsed_entities, parsed_packages = parse_string(code)
    return parsed_entities, parsed_packages


def resolve_entities_and_packages(entities, packages, must_resolve=True):
    '''
    Resolve references in entity and package objects.
    '''
    resolved_packages = package.resolve_packages(packages)
    resolved_entities = dict(
        [(e.identifier.lower(),
          e.resolve(resolved_packages, must_resolve=must_resolve))
         for e in entities])
    return resolved_entities, resolved_packages


def parse_and_resolve_files(filenames, must_resolve=True, ignore_parse_exceptions=False):
    '''
    Takes a list of filenames,
    parses them with the VUnit parser
    and then processes them into slvcodec classes.

    The packages references to one another are resolved as
    are the references to types and constants in the entity
    interfaces.
    '''

    all_entities = []
    all_packages = []
    for filename in filenames:
        try:
            entities, packages = parse_file(filename)
            all_entities += entities
            all_packages += packages
        except Exception as e:
            if ignore_parse_exceptions:
                logger.warning('Failed to parse {}.  Got error {}'.format(filename, str(e)))
            else:
                raise(e)
    resolved_entities, resolved_packages = resolve_entities_and_packages(
        entities=all_entities, packages=all_packages, must_resolve=must_resolve)
    return resolved_entities, resolved_packages
