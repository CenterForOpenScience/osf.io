'''a "gatherer" is a function that gathers metadata about a focus.

gatherers register their interests via the `@gatherer` decorator
'''
import datetime
import functools
import typing

import rdflib

from .focus import Focus


Gatherer = typing.Callable[[Focus], typing.Iterable[tuple]]
# module-private registry of gatherers by their iris of interest,
# built by the @gatherer decorator (via add_gatherer)
GathererRegistry = dict[             # outer dict maps
    typing.Optional[rdflib.URIRef],         # from focustype_iri (or None)
    dict[                            # to inner dict, which maps
        typing.Optional[rdflib.URIRef],     # from predicate_iri (or None)
        set[Gatherer],               # to a set of gatherers.
    ],
]
__gatherer_registry: GathererRegistry = {}


def gatherer(*predicate_iris, focustype_iris=None):
    """decorator to register metadata gatherer functions

    for example:
        ```
        from osf.metadata import gather

        @gather.er(DCTERMS.language, focustype_iris=[OSF.MyType])
        def gather_language(focus: gather.Focus):
            yield (DCTERMS.language, getattr(focus.dbmodel, 'language'))
        ```
    """
    def _decorator(gatherer: Gatherer):
        tidy_gatherer = _make_gatherer_tidy(gatherer)
        add_gatherer(tidy_gatherer, predicate_iris, focustype_iris)
        return tidy_gatherer
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


def get_gatherers(focustype_iri, predicate_iris):
    gatherer_set = set()
    for focustype in (None, focustype_iri):
        for_focustype = __gatherer_registry.get(focustype, {})
        for predicate in (None, *predicate_iris):
            gatherer_set.update(for_focustype.get(predicate, ()))
    return gatherer_set


class QuietlySkippleTriple(Exception):
    pass


def _make_gatherer_tidy(inner_gatherer: Gatherer) -> Gatherer:
    @functools.wraps(inner_gatherer)
    def tidy_gatherer(focus: Focus):
        for triple in inner_gatherer(focus):
            try:
                yield _tidy_gathered_triple(triple, focus)
            except QuietlySkippleTriple:
                pass
    return tidy_gatherer


def _tidy_gathered_triple(triple, focus) -> tuple:
    """
    fill in the (perhaps partial) triple, given its focus,
    and convert some common python types to rdflib representation
    """
    if len(triple) == 2:  # allow omitting subject
        triple = (focus.iri, *triple)
    if len(triple) != 3:  # triple means three
        raise ValueError(f'_defocus: not triple enough (got {triple})')
    if any((v is None or v == '') for v in triple):
        raise QuietlySkippleTriple
    subj, pred, obj = triple
    if isinstance(obj, datetime.datetime):
        # no need for finer granularity than date (TODO: is that wrong?)
        obj = obj.date()
    if isinstance(obj, datetime.date):
        # encode dates as iso8601-formatted string literals (TODO: is xsd:dateTime good?)
        obj = obj.isoformat()
    if not isinstance(obj, (Focus, rdflib.term.Node)):
        # unless a Focus or already rdflib-erated, assume it's literal
        obj = rdflib.Literal(obj)
    return (subj, pred, obj)
