from unittest import mock

import rdflib

from osf.metadata import gather
from osf.metadata.gather.gatherer import get_gatherers


fake_gatherer_registry = {}


@mock.patch('osf.metadata.gather.gatherer.__gatherer_registry', new=fake_gatherer_registry)
def test_gatherer_registry():
    fake_gatherer_registry.clear()

    FOO = rdflib.Namespace('https://foo.example/')
    BAZ = rdflib.Namespace('https://baz.example/')

    # register gatherer functions
    @gather.er(FOO.identifier)
    def gather_identifiers(focus):
        yield (FOO.identifier, 'fooid')

    @gather.er(focustype_iris=[FOO.Project])
    def gather_project_defaults(focus):
        yield (FOO.title, 'fooproject')

    @gather.er(focustype_iris=[BAZ.Preprint])
    def gather_preprint_defaults(focus):
        yield (FOO.title, 'foopreprint')
        yield (BAZ.title, 'foopreprint')

    @gather.er(BAZ.creator, focustype_iris=[FOO.Project, BAZ.Preprint])
    def gather_preprint_or_project_creator(focus):
        yield (BAZ.creator, gather.Focus(FOO['userguid'], BAZ.Agent))

    @gather.er(BAZ.creator, focustype_iris=[BAZ.Preprint])
    def gather_special_preprint_creator(focus):
        yield (BAZ.creator, gather.Focus(BAZ['special'], BAZ.Agent))

    @gather.er(FOO.name, focustype_iris=[BAZ.Agent])
    def gather_agent_name(focus):
        yield (FOO.name, 'hey is me')

    # check the registry is correct
    assert fake_gatherer_registry == {
        None: {
            FOO.identifier: {gather_identifiers},
        },
        FOO.Project: {
            None: {gather_project_defaults},
            BAZ.creator: {gather_preprint_or_project_creator},
        },
        BAZ.Preprint: {
            None: {gather_preprint_defaults},
            BAZ.creator: {gather_preprint_or_project_creator, gather_special_preprint_creator},
        },
        BAZ.Agent: {
            FOO.name: {gather_agent_name},
        },
    }

    # check get_gatherers gets good gatherers
    assert get_gatherers(FOO.Anything, [FOO.unknown]) == set()
    assert get_gatherers(FOO.Anything, [FOO.identifier]) == {
        gather_identifiers,
    }
    assert get_gatherers(FOO.Project, [BAZ.creator]) == {
        gather_project_defaults,
        gather_preprint_or_project_creator,
    }
    assert get_gatherers(BAZ.Preprint, [BAZ.creator]) == {
        gather_preprint_defaults,
        gather_preprint_or_project_creator,
        gather_special_preprint_creator,
    }
    assert get_gatherers(BAZ.Preprint, [BAZ.creator], include_focustype_defaults=False) == {
        gather_preprint_or_project_creator,
        gather_special_preprint_creator,
    }
    assert get_gatherers(BAZ.Agent, [FOO.name, FOO.identifier, FOO.unknown]) == {
        gather_agent_name,
        gather_identifiers,
    }
