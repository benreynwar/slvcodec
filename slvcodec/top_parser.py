import logging

from slvcodec import vhdl_parser, entity, package


logger = logging.getLogger(__name__)


vparser = vhdl_parser.VHDLParser(None)


def parsed_from_filename(filename):
    '''
    Parse the contents of a VHDL file using the VUnit VHDL parser.
    '''
    parsed = vparser.parse(filename)
    return parsed


def process_files(filenames, must_resolve=True):
    '''
    Takes a list of filenames,
    parses them with the VUnit parser
    and then processes them into slvcodec classes.

    The packages references to one another are resolved as
    are the references to types and constants in the entity
    interfaces.
    '''
    entities = {}
    packages = []
    for filename in filenames:
        parsed = parsed_from_filename(filename)
        if parsed.entities:
            p = entity.process_parsed_entity(parsed)
            entities[p.identifier] = p
            # Make sure that file only has one entity or one package.
            assert len(parsed.entities) == 1
            assert not parsed.packages
        if parsed.packages:
            pkg = package.process_parsed_package(parsed)
            packages.append(pkg)
    resolved_packages = package.resolve_packages(packages)
    resolved_entities = dict(
        [(e.identifier,
          e.resolve(resolved_packages, must_resolve=must_resolve))
         for e in entities.values()])
    return resolved_entities, resolved_packages
