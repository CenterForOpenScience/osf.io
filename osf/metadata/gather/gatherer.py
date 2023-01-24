'''a "gatherer" is a function that gathers metadata about a focus.

gatherers register their interests via the `@gatherer` decorator
'''
import typing

from .focus import Focus


Gatherer = typing.Callable[[Focus], typing.Iterable[tuple]]


# module-private
__gatherer_registry = {}


def gatherer(*predicate_iris, focustype_iris=None):
    """decorator to register metadata gatherer functions

    for example:
        ```
        @gatherer(DCT.language, focustype_iris=[OSF.MyType])
        def gather_language(focus: gather.Focus):
            yield (DCT.language, getattr(focus.dbmodel, 'language'))
        ```
    """
    def _decorator(gatherer_fun):
        add_gatherer(gatherer_fun, predicate_iris, focustype_iris)
        return gatherer_fun
    return _decorator


def add_gatherer(gatherer, predicate_iris, focustype_iris):
    assert (predicate_iris or focustype_iris), 'cannot register gatherer without either predicate_iris or focustype_iris'
    focustype_keys = focustype_iris or [None]
    predicate_keys = predicate_iris or [None]
    registry_keys = (
        (focustype, predicate)
        for focustype in focustype_keys
        for predicate in predicate_keys
    )
    for focustype, predicate in registry_keys:
        (
            __gatherer_registry
            .setdefault(focustype, {})
            .setdefault(predicate, set())
            .add(gatherer)
        )


def get_gatherers(predicate_iri, focustype_iri):
    gatherer_set = set()
    for focustype in (None, focustype_iri):
        for_focustype = __gatherer_registry.get(focustype, {})
        for predicate in (None, predicate_iri):
            gatherer_set.update(for_focustype.get(predicate, ()))
    return gatherer_set
