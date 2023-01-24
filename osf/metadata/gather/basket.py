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

    def __getitem__(self, slice_or_arg) -> typing.Iterable[rdflib.term.Node]:
        """for convenient getting of values
        """
        if isinstance(slice_or_arg, slice):
            focus_iri = slice_or_arg.start
            predicate = slice_or_arg.stop
            # TODO: use slice_or_arg.step for "expected type"
        else:
            focus_iri = self.focus.iri
            predicate = slice_or_arg
        yield from self.gathered_metadata.objects(focus_iri, predicate)

    def pls_gather_by_map(self, predicate_map):
        for triple in self._gather_by_map(predicate_map, self.focus):
            self.gathered_metadata.add(triple)

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
        for predicate_iri in predicate_map.keys():
            for (subj, pred, obj) in self._gather_by_predicate(predicate_iri, with_focus):
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

    def _gather_by_predicate(self, predicate_iri, with_focus=None):
        if with_focus is None:
            with_focus = self.focus
        for gatherer in get_gatherers(predicate_iri, with_focus.rdftype):
            yield from self._do_a_gathertask(gatherer, with_focus)

    def _do_a_gathertask(self, gatherer, focus):
        if (gatherer, focus) not in self._gathertasks_done:
            self._gathertasks_done.add((gatherer, focus))  # eager
            for triple in gatherer(focus):
                triple = self._defocus(triple, focus)
                if triple is not None:
                    yield (triple[0], triple[1], self._tidy_triple_object(triple[2]))

    def _defocus(self, triple, focus):
        """
        fill in the (partial) triple, given its focus,
        and blur any rough edges that are easy to see
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
