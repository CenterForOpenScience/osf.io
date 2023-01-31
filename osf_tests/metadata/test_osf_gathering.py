import datetime

from django.test import TestCase
import rdflib
from rdflib import Literal, URIRef

from api_tests.utils import create_test_file
from framework.auth import Auth
from osf.metadata import gather, osf_gathering
from osf.metadata.rdfutils import (
    FOAF,
    OSF,
    OSFIO,
    DCT,
    DOI,
    OWL,
    RDF,
    checksum_iri,
)
from osf import models as osfdb
from osf.utils import permissions
from osf_tests import factories
from website import settings as website_settings


def _get_graph_and_focuses(triples):
    graph = rdflib.Graph()
    focuses = set()
    for (subj, pred, obj) in triples:
        if isinstance(obj, gather.Focus):
            graph.add((subj, pred, obj.iri))
            focuses.add(obj)
        else:
            graph.add((subj, pred, obj))
    return graph, focuses


def _assert_triples(actual_triples, expected_triples):
    expected_graph, expected_focuses = _get_graph_and_focuses(expected_triples)
    actual_graph, actual_focuses = _get_graph_and_focuses(actual_triples)
    (in_both, in_expected, in_actual) = rdflib.compare.graph_diff(expected_graph, actual_graph)
    assert (set(in_expected), set(in_actual)) == (set(), set())
    assert expected_focuses == actual_focuses


class TestOsfGathering(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user__admin = factories.UserFactory()
        cls.user__readwrite = factories.UserFactory(
            external_identity={'ORCID': {'1234-4321-5678-8765': 'VERIFIED'}},
        )
        cls.user__readonly = factories.UserFactory(
            external_identity={'ORCID': {'1234-4321-6789-9876': 'CREATE'}},
            social={
                'profileWebsites': ['http://mysite.example', 'http://myothersite.example/foo'],
                'baiduScholar': 'blarg',
            },
        )
        cls.project = factories.ProjectFactory(creator=cls.user__admin, is_public=True)
        cls.project.add_contributor(cls.user__readwrite, permissions=permissions.WRITE)
        cls.project.add_contributor(cls.user__readonly, permissions=permissions.READ, visible=False)
        cls.file_sha256 = '876b99ba1225de6b7f55ef52b068d0da3aa2ec4271875954c3b87b6659ae3823'
        cls.file = create_test_file(
            cls.project,
            cls.user__admin,
            size=123456,
            filename='blarg.txt',
            sha256=cls.file_sha256,
        )
        cls.registration = factories.RegistrationFactory(project=cls.project, creator=cls.user__admin)
        cls.registration.registered_date = datetime.datetime(2121, 2, 1)
        cls.registration.save()
        cls.projectfocus = osf_gathering.OsfFocus(cls.project)
        cls.filefocus = osf_gathering.OsfFocus(cls.file)
        cls.registrationfocus = osf_gathering.OsfFocus(cls.registration)
        cls.userfocus__admin = osf_gathering.OsfFocus(cls.user__admin)
        cls.userfocus__readwrite = osf_gathering.OsfFocus(cls.user__readwrite)
        cls.userfocus__readonly = osf_gathering.OsfFocus(cls.user__readonly)

    def test_setupdata(self):
        assert self.projectfocus.iri == OSFIO[self.project._id]
        assert self.projectfocus.rdftype == OSF.Project
        assert self.projectfocus.dbmodel is self.project
        assert self.registrationfocus.iri == OSFIO[self.registration._id]
        assert self.registrationfocus.rdftype == OSF.Registration
        assert self.registrationfocus.dbmodel is self.registration
        assert self.filefocus.iri == OSFIO[self.file.get_guid()._id]
        assert self.filefocus.rdftype == OSF.File
        assert self.filefocus.dbmodel is self.file

    def test_gather_identifiers(self):
        # focus: project
        _assert_triples(osf_gathering.gather_identifiers(self.projectfocus), {
            (self.projectfocus.iri, DCT.identifier, Literal(self.projectfocus.iri)),
        })
        self.project.set_identifier_value('doi', '10.dot.ten/mydoi')
        _assert_triples(osf_gathering.gather_identifiers(self.projectfocus), {
            (self.projectfocus.iri, DCT.identifier, Literal(self.projectfocus.iri)),
            (self.projectfocus.iri, DCT.identifier, Literal('https://doi.org/10.dot.ten/mydoi')),
            (self.projectfocus.iri, OWL.sameAs, URIRef('https://doi.org/10.dot.ten/mydoi')),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_identifiers(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.identifier, Literal(self.registrationfocus.iri)),
        })
        self.registration.set_identifier_value('doi', '10.dot.ten/myreg')
        _assert_triples(osf_gathering.gather_identifiers(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.identifier, Literal(self.registrationfocus.iri)),
            (self.registrationfocus.iri, DCT.identifier, Literal('https://doi.org/10.dot.ten/myreg')),
            (self.registrationfocus.iri, OWL.sameAs, URIRef('https://doi.org/10.dot.ten/myreg')),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_identifiers(self.filefocus), {
            (self.filefocus.iri, DCT.identifier, Literal(self.filefocus.iri)),
        })

    def test_gather_flexible_types(self):
        # focus: project
        _assert_triples(osf_gathering.gather_flexible_types(self.projectfocus), {
            (self.projectfocus.iri, DCT.type, OSF[self.project.category]),
        })
        self.projectfocus.guid_metadata_record.resource_type_general = 'Book'
        _assert_triples(osf_gathering.gather_flexible_types(self.projectfocus), {
            (self.projectfocus.iri, DCT.type, OSF[self.project.category]),
            (self.projectfocus.iri, DCT.type, Literal('Book')),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_flexible_types(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.type, OSF[self.registration.category]),
        })
        self.registrationfocus.guid_metadata_record.resource_type_general = 'Preprint'
        _assert_triples(osf_gathering.gather_flexible_types(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.type, OSF[self.registration.category]),
            (self.registrationfocus.iri, DCT.type, Literal('Preprint')),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_flexible_types(self.filefocus), set())
        self.filefocus.guid_metadata_record.resource_type_general = 'Dataset'
        _assert_triples(osf_gathering.gather_flexible_types(self.filefocus), {
            (self.filefocus.iri, DCT.type, Literal('Dataset')),
        })

    def test_gather_created(self):
        # focus: project
        _assert_triples(osf_gathering.gather_created(self.projectfocus), {
            (self.projectfocus.iri, DCT.created, Literal(str(self.project.created.date()))),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_created(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.created, Literal('2121-02-01')),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_created(self.filefocus), {
            (self.filefocus.iri, DCT.created, Literal(str(self.file.created.date()))),
        })

    def test_gather_available(self):
        # focus: project
        _assert_triples(osf_gathering.gather_available(self.projectfocus), set())
        # focus: registration
        _assert_triples(osf_gathering.gather_available(self.registrationfocus), set())
        factories.EmbargoFactory(
            target_item=self.registration,
            user=self.user__admin,
            end_date=datetime.datetime(1973, 7, 3),
        )
        _assert_triples(osf_gathering.gather_available(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.available, Literal('1973-07-03')),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_available(self.filefocus), set())

    def test_gather_modified(self):
        # focus: project
        _assert_triples(osf_gathering.gather_modified(self.projectfocus), {
            (self.projectfocus.iri, DCT.modified, Literal(str(self.project.last_logged.date()))),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_modified(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.modified, Literal(str(self.registration.last_logged.date()))),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_modified(self.filefocus), {
            (self.filefocus.iri, DCT.modified, Literal(str(self.file.modified.date()))),
        })

    def test_gather_moderation_dates(self):
        # focus: project
        _assert_triples(osf_gathering.gather_moderation_dates(self.projectfocus), set())
        # focus: registration
        _assert_triples(osf_gathering.gather_moderation_dates(self.registrationfocus), set())
        # focus: file
        _assert_triples(osf_gathering.gather_moderation_dates(self.filefocus), set())
        # TODO: put registration thru moderation

    def test_gather_licensing(self):
        # focus: project
        _assert_triples(osf_gathering.gather_licensing(self.projectfocus), set())
        self.project.node_license = factories.NodeLicenseRecordFactory(
            year='1952-2001',
            copyright_holders=['foo', 'bar', 'baz baz'],
        )
        _assert_triples(osf_gathering.gather_licensing(self.projectfocus), {
            (self.projectfocus.iri, DCT.dateCopyrighted, Literal('1952-2001')),
            (self.projectfocus.iri, DCT.rightsHolder, Literal('foo')),
            (self.projectfocus.iri, DCT.rightsHolder, Literal('bar')),
            (self.projectfocus.iri, DCT.rightsHolder, Literal('baz baz')),
            (self.projectfocus.iri, DCT.rights, Literal('No license')),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_licensing(self.registrationfocus), set())
        self.registration.node_license = factories.NodeLicenseRecordFactory(
            year='1957-2008',
            copyright_holders=['bar bar', 'baz baz', 'quux'],
            node_license=osfdb.NodeLicense.objects.get(
                name='CC-By Attribution 4.0 International',
            ),
        )
        expected_license_iri = URIRef('https://creativecommons.org/licenses/by/4.0/legalcode')
        _assert_triples(osf_gathering.gather_licensing(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.dateCopyrighted, Literal('1957-2008')),
            (self.registrationfocus.iri, DCT.rightsHolder, Literal('bar bar')),
            (self.registrationfocus.iri, DCT.rightsHolder, Literal('baz baz')),
            (self.registrationfocus.iri, DCT.rightsHolder, Literal('quux')),
            (self.registrationfocus.iri, DCT.rights, expected_license_iri),
            (expected_license_iri, FOAF.name, Literal('CC-By Attribution 4.0 International')),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_licensing(self.filefocus), set())

    def test_gather_title(self):
        # focus: project
        _assert_triples(osf_gathering.gather_title(self.projectfocus), {
            (self.projectfocus.iri, DCT.title, Literal(self.project.title)),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_title(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.title, Literal(self.registration.title)),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_title(self.filefocus), set())
        self.filefocus.guid_metadata_record.title = 'my title!'
        _assert_triples(osf_gathering.gather_title(self.filefocus), {
            (self.filefocus.iri, DCT.title, Literal('my title!')),
        })

    def test_gather_language(self):
        # focus: project
        _assert_triples(osf_gathering.gather_language(self.projectfocus), set())
        self.projectfocus.guid_metadata_record.language = 'es'
        _assert_triples(osf_gathering.gather_language(self.projectfocus), {
            (self.projectfocus.iri, DCT.language, Literal('es')),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_language(self.registrationfocus), set())
        self.registrationfocus.guid_metadata_record.language = 'es'
        _assert_triples(osf_gathering.gather_language(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.language, Literal('es')),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_language(self.filefocus), set())
        self.filefocus.guid_metadata_record.language = 'es'
        _assert_triples(osf_gathering.gather_language(self.filefocus), {
            (self.filefocus.iri, DCT.language, Literal('es')),
        })

    def test_gather_description(self):
        # focus: project
        _assert_triples(osf_gathering.gather_description(self.projectfocus), {
            (self.projectfocus.iri, DCT.description, Literal(self.project.description)),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_description(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.description, Literal(self.registration.description)),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_description(self.filefocus), set())
        self.filefocus.guid_metadata_record.description = 'woop a doo'
        _assert_triples(osf_gathering.gather_description(self.filefocus), {
            (self.filefocus.iri, DCT.description, Literal('woop a doo')),
        })

    def test_gather_keywords(self):
        # focus: project
        _assert_triples(osf_gathering.gather_keywords(self.projectfocus), set())
        self.project.update_tags(['woop', 'a', 'doo'], auth=Auth(self.user__admin))
        _assert_triples(osf_gathering.gather_keywords(self.projectfocus), {
            (self.projectfocus.iri, OSF.keyword, Literal('woop')),
            (self.projectfocus.iri, OSF.keyword, Literal('a')),
            (self.projectfocus.iri, OSF.keyword, Literal('doo')),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_keywords(self.registrationfocus), set())
        self.registration.update_tags(['boop', 'a', 'doop'], auth=Auth(self.user__admin))
        _assert_triples(osf_gathering.gather_keywords(self.registrationfocus), {
            (self.registrationfocus.iri, OSF.keyword, Literal('boop')),
            (self.registrationfocus.iri, OSF.keyword, Literal('a')),
            (self.registrationfocus.iri, OSF.keyword, Literal('doop')),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_keywords(self.filefocus), set())

    def test_gather_subjects(self):
        # focus: project
        _assert_triples(osf_gathering.gather_subjects(self.projectfocus), set())
        subjects = [
            factories.SubjectFactory(text='Bloomy'),
        ]
        self.project.set_subjects([[s._id] for s in subjects], auth=Auth(self.user__admin))
        _assert_triples(osf_gathering.gather_subjects(self.projectfocus), {
            (self.projectfocus.iri, DCT.subject, Literal('Bloomy')),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_subjects(self.registrationfocus), set())
        subjects = [
            factories.SubjectFactory(text='Other Teacher Education and Professional Development'),
            factories.SubjectFactory(text='Applied Mechanics'),
        ]
        self.registration.set_subjects([[s._id] for s in subjects], auth=Auth(self.user__admin))
        _assert_triples(osf_gathering.gather_subjects(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.subject, Literal('Other Teacher Education and Professional Development')),
            (self.registrationfocus.iri, DCT.subject, Literal('Applied Mechanics')),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_subjects(self.filefocus), set())

    def test_gather_file_basics(self):
        # focus: project
        _assert_triples(osf_gathering.gather_file_basics(self.projectfocus), set())
        # focus: registration
        _assert_triples(osf_gathering.gather_file_basics(self.registrationfocus), set())
        # focus: file
        _assert_triples(osf_gathering.gather_file_basics(self.filefocus), {
            (self.filefocus.iri, OSF.file_name, Literal(self.file.name)),
            (self.filefocus.iri, OSF.file_path, Literal(self.file.materialized_path)),
        })

    def test_gather_versions(self):
        # focus: project
        _assert_triples(osf_gathering.gather_versions(self.projectfocus), set())
        # focus: registration
        _assert_triples(osf_gathering.gather_versions(self.registrationfocus), set())
        # focus: file
        fileversion = self.file.versions.first()
        fileversion_iri = URIRef(
            f'{website_settings.API_DOMAIN}v2/files/{self.file._id}/versions/{fileversion.identifier}/',
        )
        _assert_triples(osf_gathering.gather_versions(self.filefocus), {
            (self.filefocus.iri, DCT.hasVersion, fileversion_iri),
            (fileversion_iri, RDF.type, OSF.FileVersion),
            (fileversion_iri, DCT.creator, osf_gathering.OsfFocus(fileversion.creator)),
            (fileversion_iri, DCT.created, Literal(str(fileversion.created.date()))),
            (fileversion_iri, DCT.modified, Literal(str(fileversion.modified.date()))),
            (fileversion_iri, DCT['format'], Literal(fileversion.content_type)),
            (fileversion_iri, DCT.extent, Literal('0.118 MB')),
            (fileversion_iri, OSF.version_number, Literal(fileversion.identifier)),
            (fileversion_iri, DCT.requires, checksum_iri('sha-256', self.file_sha256))
        })

    def test_gather_files(self):
        # focus: project
        _assert_triples(osf_gathering.gather_files(self.projectfocus), {
            (self.projectfocus.iri, DCT.hasPart, self.filefocus),
            (self.projectfocus.iri, OSF.has_file, self.filefocus),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_files(self.registrationfocus), {
            # (self.registrationfocus.iri, DCT.hasPart, self.filefocus),
            # (self.registrationfocus.iri, OSF.has_file, self.filefocus),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_files(self.filefocus), set())

    def test_gather_parts(self):
        # focus: project
        _assert_triples(osf_gathering.gather_parts(self.projectfocus), set())
        # ...with components:
        component = factories.ProjectFactory(parent=self.project, creator=self.user__admin, is_public=True)
        sibcomponent = factories.ProjectFactory(parent=self.project, creator=self.user__admin, is_public=True)
        subcomponent = factories.ProjectFactory(parent=component, creator=self.user__admin, is_public=True)
        componentfocus = osf_gathering.OsfFocus(component)
        sibcomponentfocus = osf_gathering.OsfFocus(sibcomponent)
        subcomponentfocus = osf_gathering.OsfFocus(subcomponent)
        _assert_triples(osf_gathering.gather_parts(self.projectfocus), {
            (self.projectfocus.iri, DCT.hasPart, componentfocus),
            (self.projectfocus.iri, DCT.hasPart, sibcomponentfocus),
            (self.projectfocus.iri, DCT.hasPart, subcomponentfocus),
            (self.projectfocus.iri, OSF.has_child, componentfocus),
            (self.projectfocus.iri, OSF.has_child, sibcomponentfocus),
            (self.projectfocus.iri, OSF.has_descendent, subcomponentfocus),
        })
        _assert_triples(osf_gathering.gather_parts(componentfocus), {
            (componentfocus.iri, DCT.isPartOf, self.projectfocus),
            (componentfocus.iri, OSF.has_root, self.projectfocus),
            (componentfocus.iri, OSF.has_parent, self.projectfocus),
            (componentfocus.iri, DCT.hasPart, subcomponentfocus),
            (componentfocus.iri, OSF.has_child, subcomponentfocus),
        })
        _assert_triples(osf_gathering.gather_parts(sibcomponentfocus), {
            (sibcomponentfocus.iri, DCT.isPartOf, self.projectfocus),
            (sibcomponentfocus.iri, OSF.has_parent, self.projectfocus),
            (sibcomponentfocus.iri, OSF.has_root, self.projectfocus),
        })
        _assert_triples(osf_gathering.gather_parts(subcomponentfocus), {
            (subcomponentfocus.iri, DCT.isPartOf, componentfocus),
            (subcomponentfocus.iri, DCT.isPartOf, self.projectfocus),
            (subcomponentfocus.iri, OSF.has_parent, componentfocus),
            (subcomponentfocus.iri, OSF.has_root, self.projectfocus),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_parts(self.registrationfocus), set())
        # focus: file
        _assert_triples(osf_gathering.gather_parts(self.filefocus), {
            (self.filefocus.iri, DCT.isPartOf, self.projectfocus),
        })

    def test_gather_related_items(self):
        # focus: project
        _assert_triples(osf_gathering.gather_related_items(self.projectfocus), set())
        self.project.article_doi = '10.onezero/foo'
        _assert_triples(osf_gathering.gather_related_items(self.projectfocus), {
            (self.projectfocus.iri, DCT.relation, DOI[self.project.article_doi]),
            (self.projectfocus.iri, OSF.is_supplement_to_article, DOI[self.project.article_doi]),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_related_items(self.registrationfocus), set())
        self.registration.article_doi = '10.blarg/blerg'
        _assert_triples(osf_gathering.gather_related_items(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.relation, DOI[self.registration.article_doi]),
            (self.registrationfocus.iri, OSF.is_supplement_to_article, DOI[self.registration.article_doi]),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_related_items(self.filefocus), set())

    def test_gather_agents(self):
        # focus: project
        _assert_triples(osf_gathering.gather_agents(self.projectfocus), {
            (self.projectfocus.iri, DCT.creator, self.userfocus__admin),
            (self.projectfocus.iri, DCT.creator, self.userfocus__readwrite),
            (self.projectfocus.iri, DCT.contributor, self.userfocus__readonly),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_agents(self.registrationfocus), {
            (self.registrationfocus.iri, DCT.creator, self.userfocus__admin),
            (self.registrationfocus.iri, DCT.creator, self.userfocus__readwrite),
            (self.registrationfocus.iri, DCT.contributor, self.userfocus__readonly),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_agents(self.filefocus), set())

    def test_gather_affiliated_institutions(self):
        # focus: project
        _assert_triples(osf_gathering.gather_affiliated_institutions(self.projectfocus), set())
        _assert_triples(osf_gathering.gather_affiliated_institutions(self.userfocus__admin), set())
        institution = factories.InstitutionFactory()
        institution_iri = URIRef(institution.identifier_domain)
        self.user__admin.add_or_update_affiliated_institution(institution)
        self.project.add_affiliated_institution(institution, self.user__admin)
        _assert_triples(osf_gathering.gather_affiliated_institutions(self.projectfocus), {
            (self.projectfocus.iri, OSF.affiliated_institution, institution_iri),
            (institution_iri, FOAF.name, Literal(institution.name)),
            (institution_iri, DCT.identifier, Literal(institution.identifier_domain)),
        })
        # focus: user
        _assert_triples(osf_gathering.gather_affiliated_institutions(self.userfocus__admin), {
            (self.userfocus__admin.iri, OSF.affiliated_institution, institution_iri),
            (institution_iri, FOAF.name, Literal(institution.name)),
            (institution_iri, DCT.identifier, Literal(institution.identifier_domain)),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_affiliated_institutions(self.registrationfocus), set())
        # focus: file
        _assert_triples(osf_gathering.gather_affiliated_institutions(self.filefocus), set())

    def test_gather_funding(self):
        # focus: project
        _assert_triples(osf_gathering.gather_funding(self.projectfocus), set())
        self.projectfocus.guid_metadata_record.funding_info = [
            {'funder_name': 'hooray'},
            {
                'funder_name': 'NIH',
                'funder_identifier': 'https://doi.org/10.fake/NIH',
                'funder_identifier_type': 'Crossref Funder ID',
                'award_title': 'big fun',
                'award_uri': 'https://nih.example/award',
                'award_number': '27',
            },
        ]
        bnode1 = rdflib.BNode()
        bnode2 = rdflib.BNode()
        _assert_triples(osf_gathering.gather_funding(self.projectfocus), {
            (self.projectfocus.iri, OSF.funder, bnode1),
            (bnode1, RDF.type, OSF.Funder),
            (bnode1, FOAF.name, Literal('hooray')),
            (self.projectfocus.iri, OSF.funder, bnode2),
            (bnode2, RDF.type, OSF.Funder),
            (bnode2, FOAF.name, Literal('NIH')),
            (bnode2, DCT.identifier, Literal('https://doi.org/10.fake/NIH')),
            (bnode2, OSF.funder_identifier_type, Literal('Crossref Funder ID')),
            (bnode2, OSF.award_number, Literal('27')),
            (bnode2, OSF.award_uri, Literal('https://nih.example/award')),
            (bnode2, OSF.award_title, Literal('big fun')),
        })
        # focus: registration
        _assert_triples(osf_gathering.gather_funding(self.registrationfocus), set())
        self.registrationfocus.guid_metadata_record.funding_info = [
            {'funder_name': 'blooray'},
        ]
        bnode1 = rdflib.BNode()
        _assert_triples(osf_gathering.gather_funding(self.registrationfocus), {
            (self.registrationfocus.iri, OSF.funder, bnode1),
            (bnode1, RDF.type, OSF.Funder),
            (bnode1, FOAF.name, Literal('blooray')),
        })
        # focus: file
        _assert_triples(osf_gathering.gather_funding(self.filefocus), set())
        self.filefocus.guid_metadata_record.funding_info = [
            {'funder_name': 'exray'},
        ]
        bnode1 = rdflib.BNode()
        _assert_triples(osf_gathering.gather_funding(self.filefocus), {
            (self.filefocus.iri, OSF.funder, bnode1),
            (bnode1, RDF.type, OSF.Funder),
            (bnode1, FOAF.name, Literal('exray')),
        })

    def test_gather_user_basics(self):
        # focus: admin user
        _assert_triples(osf_gathering.gather_user_basics(self.userfocus__admin), {
            (self.userfocus__admin.iri, RDF.type, DCT.Agent),
            (self.userfocus__admin.iri, FOAF.name, Literal(self.user__admin.fullname)),
        })
        # focus: readwrite user
        _assert_triples(osf_gathering.gather_user_basics(self.userfocus__readwrite), {
            (self.userfocus__readwrite.iri, RDF.type, DCT.Agent),
            (self.userfocus__readwrite.iri, FOAF.name, Literal(self.user__readwrite.fullname)),
            (self.userfocus__readwrite.iri, DCT.identifier, Literal('https://orcid.org/1234-4321-5678-8765')),
            (self.userfocus__readwrite.iri, OWL.sameAs, URIRef('https://orcid.org/1234-4321-5678-8765')),
        })
        # focus: readonly user
        _assert_triples(osf_gathering.gather_user_basics(self.userfocus__readonly), {
            (self.userfocus__readonly.iri, RDF.type, DCT.Agent),
            (self.userfocus__readonly.iri, FOAF.name, Literal(self.user__readonly.fullname)),
            # orcid not verified, should be excluded
            (self.userfocus__readonly.iri, DCT.identifier, Literal('http://mysite.example')),
            (self.userfocus__readonly.iri, DCT.identifier, Literal('http://myothersite.example/foo')),
            (self.userfocus__readonly.iri, DCT.identifier, Literal('http://xueshu.baidu.com/scholarID/blarg')),
        })
