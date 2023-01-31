import rdflib


class Focus:
    '''the "focus" is what to gather metadata about.
    '''
    iri: rdflib.URIRef
    rdftype: rdflib.URIRef  # TODO: allow multiple types, but don't make a big deal about it

    def __init__(self, iri, rdftype, dbmodel=None):
        assert (iri and rdftype)
        self.iri = iri
        self.rdftype = rdftype
        self.dbmodel = dbmodel  # TODO: improve gardeners to keep this out of Focus

    def __eq__(self, other):
        return (
            isinstance(other, Focus)
            and (self.iri, self.rdftype) == (other.iri, other.rdftype)
        )

    def __hash__(self):
        return hash((self.iri, self.rdftype))
