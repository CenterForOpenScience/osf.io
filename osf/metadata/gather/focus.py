import typing
from rdflib.term import Node, URIRef

from osf.metadata import rdfutils


class Focus:
    '''the "focus" is what to gather metadata about.
    '''
    iri: URIRef
    rdftype: URIRef  # TODO: allow multiple types, but don't make a big deal about it

    def __init__(self, iri, rdftype):
        assert (iri and rdftype)
        assert isinstance(iri, URIRef)
        assert isinstance(rdftype, URIRef)
        self.iri = iri
        self.rdftype = rdftype

    def __eq__(self, other):
        return (
            isinstance(other, Focus)
            and (self.iri, self.rdftype) == (other.iri, other.rdftype)
        )

    def __hash__(self):
        return hash((self.iri, self.rdftype))

    def __repr__(self):
        return f'{self.__class__.__name__}(iri={self.iri}, rdftype={self.rdftype})'

    def __str__(self):
        return repr(self)

    def reference_triples(self) -> typing.Iterable[tuple[Node, Node, Node]]:
        yield self.iri, rdfutils.RDF.type, self.rdftype
