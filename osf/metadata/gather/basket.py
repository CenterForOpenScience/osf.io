'''a gather.Basket holds gathered metadata and coordinates gatherer actions.

'''
import typing

import rdflib

from osf.metadata import rdfutils
from .focus import Focus
from .gatherer import get_gatherers, Gatherer


class Basket:
    focus: Focus                     # the thing to gather metadata from.
    gathered_metadata: rdflib.Graph  # heap of metadata already gathered.
    _gathertasks_done: set           # memory of gatherings already done.
    _known_focus_dict: dict

    def __init__(self, focus: Focus):
        assert isinstance(focus, Focus)
        self.focus = focus
        self.reset()  # start with an empty basket (except the focus itself)

    def reset(self):
        self._gathertasks_done = set()
        self._known_focus_dict = {}
        self.gathered_metadata = rdfutils.contextualized_graph()
        self._add_focus_reference(self.focus)

    def pls_gather(self, predicate_map):  # TODO: async
        '''go gatherers, go!

        @predicate_map: dict with rdflib.URIRef keys

        use the predicate_map to get all relevant gatherers,
        ask them to gather metadata about this basket's focus,
        and keep the gathered metadata in this basket.

        for example:
        ```
        basket.pls_gather({
            DCTERMS.title: None,            # request the focus item's DCTERMS.title(s)
            DCTERMS.relation: {             # request the focus item's DCTERMS.relation(s)
                DCTERMS.title: None,        #   ...and that related item's DCTERMS.title(s)
                DCTERMS.creator: {          #   ...and that related item's DCTERMS.creator(s)
                    FOAF.name: None,    #       ...and those creators' FOAF.name(s)
                },
            },
        })
        '''
        self._do_gather(self.focus, predicate_map)

    def __getitem__(self, slice_or_arg) -> typing.Iterable[rdflib.term.Node]:
        '''convenience for getting values from the basket

        basket[subject:path] -> generator of objects that complete the rdf triple
        basket[path] -> same, with this basket's focus as the implicit subject

        if this isn't enough, access basket.gathered_metadata directly (or improve this!)
        '''
        if isinstance(slice_or_arg, slice):
            focus_iri = slice_or_arg.start
            path = slice_or_arg.stop
            # TODO: use slice_or_arg.step to constrain "expected type"
        else:
            focus_iri = self.focus.iri
            path = slice_or_arg
        self._maybe_gather_for_path(focus_iri, path)
        yield from self.gathered_metadata.objects(focus_iri, path)

    def __contains__(self, item):
        # implemented to prevent `x in basket` calling __getitem__ with every integer
        return (item in self.gathered_metadata)

    ##### END public api #####

    def _maybe_gather_for_path(self, focus, path):
        if isinstance(path, str):
            self._maybe_gather_for_predicate_map(focus, [path])
        elif isinstance(path, rdflib.paths.AlternativePath):
            self._maybe_gather_for_predicate_map(focus, set(path.args))
        elif isinstance(path, rdflib.paths.SequencePath):
            predicate_map = current_map = {}
            for subpath in path.args:
                current_map[subpath] = current_map = {}
            self._maybe_gather_for_predicate_map(focus, predicate_map)
        else:
            raise ValueError(f'unsupported path type {type(path)} (path={path})')

    def _maybe_gather_for_predicate_map(self, iri_or_focus, predicate_map):
        if isinstance(iri_or_focus, Focus):
            self._do_gather(iri_or_focus, predicate_map)
        elif isinstance(iri_or_focus, rdflib.URIRef):
            for focus in self._known_focus_dict.get(iri_or_focus, ()):
                self._do_gather(focus, predicate_map)
        elif isinstance(iri_or_focus, rdflib.BNode):
            pass  # silently ignore
        else:
            raise ValueError(f'expected `iri_or_focus` to be Focus or URIRef (got {iri_or_focus})')

    def _do_gather(self, focus, predicate_map):
        if not isinstance(predicate_map, dict):
            # allow iterable of predicates with no deeper paths
            predicate_map = {
                predicate_iri: None
                for predicate_iri in predicate_map
            }
        for gatherer in get_gatherers(focus.rdftype, predicate_map.keys()):
            for (subj, pred, obj) in self._do_a_gathertask(gatherer, focus):
                if isinstance(obj, Focus):
                    self._add_focus_reference(obj)
                    self.gathered_metadata.add((subj, pred, obj.iri))
                    if subj == focus.iri:
                        next_steps = predicate_map.get(pred, None)
                        if next_steps:
                            self._do_gather(
                                focus=obj,
                                predicate_map=next_steps,
                            )
                else:
                    self.gathered_metadata.add((subj, pred, obj))

    def _do_a_gathertask(self, gatherer: Gatherer, focus: Focus):
        '''invoke gatherer with the given focus, but only if it hasn't already been done
        '''
        if (gatherer, focus) not in self._gathertasks_done:
            self._gathertasks_done.add((gatherer, focus))  # eager
            yield from gatherer(focus)

    def _add_focus_reference(self, focus: Focus):
        (
            self._known_focus_dict
            .setdefault(focus.iri, set())
            .add(focus)
        )
        for triple in focus.reference_triples():
            self.gathered_metadata.add(triple)
