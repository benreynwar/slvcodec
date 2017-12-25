import logging


logger = logging.getLogger(__name__)


class ResolutionError(Exception):
    pass


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
      `resolved`: a dictionary of resolved items.
    '''
    updated_available = available.copy()
    unresolved_names = list(unresolved.keys())
    available_names = list(available.keys())
    assert not set(unresolved_names) & set(available_names)
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
            elif not set(item_dependencies) - set(available_names):
                any_changes = True
                failed_to_resolve = False
                try:
                    resolved_item = resolve_function(
                        unresolved_name, unresolved_item, updated_available)
                except Exception:
                    logger.error('Failed to resolve %s.  Error caught when resolving.',
                                 unresolved_name)
                    failed[unresolved_name] = unresolved_item
                    failed_names.append(unresolved_name)
                    failed_to_resolve = True
                if not failed_to_resolve:
                    assert unresolved_name not in resolved
                    resolved[unresolved_name] = resolved_item
                    assert unresolved_name not in updated_available
                    updated_available[unresolved_name] = resolved_item
                    assert unresolved_name not in available_names
                    available_names.append(unresolved_name)
        if not any_changes:
            logger.debug('Failed to resolve %s', str(unresolved_names))
            for unresolved_name in unresolved_names:
                unresolved_item = unresolved[unresolved_name]
                logger.debug(
                    '%s was missing the dependencies: %s',
                    unresolved_name,
                    str(set(dependencies[unresolved_name]) - set(available_names)))
                failed[unresolved_name] = unresolved_item
                failed_names.append(unresolved_name)
        unresolved_names = list(set(unresolved_names) - set(available_names) -
                                set(failed_names))
    return resolved, failed
