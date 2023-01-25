'''a gather.Basket holds gathered metadata and coordinates gatherer actions.

'''
import datetime
import typing

import rdflib

from osf.metadata import rdfutils
from .focus import Focus
from .gatherer import get_gatherers


class Basket:
    focus: Focus                     # the thing to gather metadata from.
    gathered_metadata: rdflib.Graph  # heap of metadata already gathered.
    _gathertasks_done: set           # memory of gatherings already done.

    def __init__(self, focus: Focus):
        self.focus = focus
        self.reset()  # start with an empty basket

    def reset(self):
        self.gathered_metadata = rdfutils.contextualized_graph()
        self._gathertasks_done = set()

    def pls_gather_by_map(self, predicate_map):
        '''go gatherers, go!

        @predicate_map: dict with rdflib.URIRef keys

        use the predicate_map to get all relevant gatherers,
        ask them to gather metadata about this basket's focus,
        and keep the gathered metadata in this basket.

        for example:
        ```
        basket.pls_gather_by_map({
            DCT.title: None,            # request the focus item's DCT.title(s)
            DCT.relation: {             # request the focus item's DCT.relation(s)
                DCT.title: None,        #   ...and that related item's DCT.title(s)
                DCT.creator: {          #   ...and that related item's DCT.creator(s)
                    FOAF.name: None,    #       ...and those creators' FOAF.name(s)
                },
            },
        })
        '''
        for triple in self._gather_by_map(predicate_map, self.focus):
            self.gathered_metadata.add(triple)

    def __getitem__(self, slice_or_arg) -> typing.Iterable[rdflib.term.Node]:
        '''convenience for getting values from the basket

        basket[subject:predicate] -> generator of objects that complete the rdf triple
        basket[predicate] -> same, with this basket's focus as the implicit subject

        if this isn't enough, access basket.gathered_metadata directly (or improve this!)
        '''
        if isinstance(slice_or_arg, slice):
            focus_iri = slice_or_arg.start
            predicate = slice_or_arg.stop
            # TODO: use slice_or_arg.step to constrain "expected type"
        else:
            focus_iri = self.focus.iri
            predicate = slice_or_arg
        yield from self.gathered_metadata.objects(focus_iri, predicate)

    ##### END public api #####

    def _gather_by_map(self, predicate_map, with_focus=None):
        if with_focus is None:
            with_focus = self.focus
        yield (with_focus.iri, rdfutils.RDF.type, with_focus.rdftype)
        if not predicate_map:
            return
        if not isinstance(predicate_map, dict):
            # allow iterable of predicates with no deeper paths
            predicate_map = {
                predicate_iri: None
                for predicate_iri in predicate_map
            }
        for (subj, pred, obj) in self._gather_by_predicates(predicate_map.keys(), with_focus):
            if isinstance(obj, Focus):
                yield (subj, pred, obj.iri)
                if subj == with_focus.iri:
                    next_steps = predicate_map.get(pred, None)
                    if next_steps:
                        yield from self._gather_by_map(
                            next_steps,
                            with_focus=obj,
                        )
            else:
                yield (subj, pred, obj)

    def _gather_by_predicates(self, predicate_iris, with_focus=None):
        if with_focus is None:
            with_focus = self.focus
        for gatherer in get_gatherers(with_focus.rdftype, predicate_iris):
            yield from self._do_a_gathertask(gatherer, with_focus)

    def _do_a_gathertask(self, gatherer, focus):
        '''invoke gatherer with the given focus, but only if it hasn't already been done
        '''
        if (gatherer, focus) not in self._gathertasks_done:
            self._gathertasks_done.add((gatherer, focus))  # eager
            for triple in gatherer(focus):
                triple = self._defocus(triple, focus)
                if triple is not None:
                    yield (triple[0], triple[1], self._tidy_triple_object(triple[2]))

    def _defocus(self, triple, focus):
        """
        fill in the (partial) triple, given its focus
        """
        if len(triple) == 2:  # allow omitting subject
            triple = (focus.iri, *triple)
        if len(triple) != 3:  # triple means three
            raise ValueError(f'{self.__class__.__name__}._defocus: not triple enough (got {triple})')
        if any((v is None or v == '') for v in triple):
            return None  # politely skipple this triple
        return triple

    def _tidy_triple_object(self, triple_object):
        """
        convert some common python types to rdflib representation
        """
        if isinstance(triple_object, datetime.datetime):
            # no need for finer granularity than date (TODO: is that wrong?)
            triple_object = triple_object.date()
        if isinstance(triple_object, datetime.date):
            # encode dates as iso8601-formatted string literals (TODO: is xsd:dateTime good?)
            triple_object = triple_object.isoformat()
        if not isinstance(triple_object, (Focus, rdflib.term.Node)):
            # unless already rdflib-erated, assume it's literal
            triple_object = rdflib.Literal(triple_object)
        return triple_object
