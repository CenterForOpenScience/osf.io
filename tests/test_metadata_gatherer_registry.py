from unittest import mock

import rdflib

from osf.metadata import gather
from osf.metadata.gather.gatherer import get_gatherers
from osf.metadata.rdfutils import (
    DCT,
    FOAF,
    OSF,
    OSFIO,
)


fake_gatherer_registry = {}


@mock.patch('osf.metadata.gather.gatherer.__gatherer_registry', new=fake_gatherer_registry)
def test_gatherer_registry():
    fake_gatherer_registry.clear()

    # register gatherer functions
    @gather.er(DCT.identifier)
    def gather_identifiers(focus):
        yield (DCT.identifier, 'fooid')

    @gather.er(focustype_iris=[OSF.Project])
    def gather_project_defaults(focus):
        yield (DCT.title, 'fooproject')

    @gather.er(focustype_iris=[OSF.Preprint])
    def gather_preprint_defaults(focus):
        yield (DCT.title, 'foopreprint')

    @gather.er(DCT.creator, focustype_iris=[OSF.Project, OSF.Preprint])
    def gather_preprint_or_project_creator(focus):
        yield (DCT.creator, Focus(OSFIO['userguid'], DCT.Agent))

    @gather.er(DCT.creator, focustype_iris=[OSF.Preprint])
    def gather_special_preprint_creator(focus):
        yield (DCT.creator, Focus(OSFIO['blah'], DCT.Agent))

    @gather.er(FOAF.name, focustype_iris=[DCT.Agent])
    def gather_agent_name(focus):
        yield (FOAF.name, 'hey is me')

    # check the registry is correct
    assert fake_gatherer_registry == {
        None: {
            DCT.identifier: {gather_identifiers},
        },
        OSF.Project: {
            None: {gather_project_defaults},
            DCT.creator: {gather_preprint_or_project_creator},
        },
        OSF.Preprint: {
            None: {gather_preprint_defaults},
            DCT.creator: {gather_preprint_or_project_creator, gather_special_preprint_creator},
        },
        DCT.Agent: {
            FOAF.name: {gather_agent_name},
        },
    }

    # check get_gatherers gets good gatherers
    FOO = rdflib.Namespace('https://foo.example/')
    assert get_gatherers(FOO.Anything, [FOO.unknown]) == set()
    assert get_gatherers(FOO.Anything, [DCT.identifier]) == {
        gather_identifiers,
    }
    assert get_gatherers(OSF.Project, [DCT.creator]) == {
        gather_project_defaults,
        gather_preprint_or_project_creator,
    }
    assert get_gatherers(OSF.Preprint, [DCT.creator]) == {
        gather_preprint_defaults,
        gather_preprint_or_project_creator,
        gather_special_preprint_creator,
    }
    assert get_gatherers(DCT.Agent, [FOAF.name, DCT.identifier, FOO.unknown]) == {
        gather_agent_name,
        gather_identifiers,
    }
