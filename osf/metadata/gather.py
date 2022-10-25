import datetime
import itertools
import rdflib

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Min, Q

from osf import models as osfdb
from osf.utils import workflows as osfworkflows

from website import settings as website_settings


__all__ = ('gather_guid_graph',)


OSF = rdflib.Namespace('https://osf.io/vocab/2022/')
DCT = rdflib.DCTERMS
A = rdflib.RDF.type


def gather_guid_graph(guid: str, max_guids: int = 1) -> rdflib.Graph:
    """gather metadata about the guid's referent and related guid-items

    @param guid: osf guid (the five-ish character string)
    @param max_guids: maximum number of guids to visit (default 1, for a sparse record)
    @returns rdflib.Graph
    """
    guids_visited = set()
    guids_to_visit = set((guid,))
    graph = _contextualized_graph()
    while (guids_to_visit and len(guids_visited) < max_guids):
        guid = guids_to_visit.pop()
        if guid in guids_visited:
            continue
        guids_visited.add(guid)
        gatherer = MetadataGatherer(guid)
        for triple in gatherer.gather_triples():
            graph.add(triple)
            (_, _, triple_object) = triple
            obj_guid = _try_guid_from_irl(triple_object)
            if obj_guid:
                guids_to_visit.add(obj_guid)
    return graph


def _contextualized_graph():
    g = rdflib.Graph()
    g.bind('osf', OSF)
    g.bind('dct', DCT)
    return g


def _guid_irl(guid):
    """return a rdflib.URIRef or None

    "URI": "uniform resource identifier"
    "URL": "uniform resource locator" (a URI that is expected to resolve)
    "IRI": "internationalized resource identifier"
    "IRL": "internationalized resource locator" (an IRI that is expected to resolve)

    @param guid: a string, Guid instance, or another model instance that has a Guid
    @returns rdflib.URIRef or None
    """
    if hasattr(guid, 'guids'):  # quacks like a Guid referent
        guid = guid.guids.first()
    if hasattr(guid, '_id'):  # quacks like a Guid instance
        guid = guid._id
    if not guid:
        return None  # politely skipple this triple
    if not isinstance(guid, str):
        raise ValueError('_guid_irl expects str, guid instance, or guid referent')
    return rdflib.URIRef(guid, base=website_settings.DOMAIN)


def _try_guid_from_irl(irl):
    if isinstance(irl, rdflib.URIRef) and irl.startswith(website_settings.DOMAIN):
        path = irl[len(website_settings.DOMAIN):].strip('/')
        if '/' not in path:
            return path
    return None


def _checksum_urn(checksum_algorithm, checksum_hex):
    urn = f'urn:checksum/{checksum_algorithm}/{checksum_hex}'
    return rdflib.URIRef(urn)


class MetadataGatherer:
    """for gathering metadata about a specific guid-identified object
    """
    def __init__(self, guid_id):
        # the "focus" is what's identified by the guid; what to gather metadata about.
        self.focus = osfdb.Guid.load(guid_id).referent
        self.focus_irl = _guid_irl(guid_id)

    def gather_triples(self):
        """
        @returns Iterable<(s, p, o)> (tuples of three rdflib.term.Node)
        """
        # `_gather_*` methods yield either `(subject, predicate, object)`
        # triples or `(predicate, object)` "twoples" (with self.focus as
        # the implicit subject -- see `_tidy_triple` for other conveniences)
        all_triples = itertools.chain(
            self._gather_identifiers(),
            self._gather_types(),
            self._gather_dates(),
            self._gather_license(),
            self._gather_text(),
            self._gather_keywords(),
            self._gather_subjects(),
            self._gather_file_specifics(),
            self._gather_parts(),
            self._gather_related_items(),
            self._gather_agents(),
            # TODO: self._gather_custom_metadata(),
        )
        tidy_triples = map(self._tidy_triple, all_triples)
        yield from filter(None, tidy_triples)

    def _gather_identifiers(self):
        for guid in self.focus.guids.all().values_list('_id', flat=True):
            yield (DCT.identifier, _guid_irl(guid))

        if hasattr(self.focus, 'get_identifier_irl'):
            doi_irl = self.focus.get_identifier_irl('doi')
            if doi_irl:
                yield (DCT.identifier, rdflib.URIRef(doi_irl))

    def _gather_types(self):
        # TODO: use rdf classes built from osf-map shapes
        # TODO: map types explicitly, don't expose internal names
        yield (A, OSF[self.focus.__class__.__name__])
        if isinstance(self.focus, osfdb.AbstractNode):
            yield (DCT.type, DCT.Collection)
        category = getattr(self.focus, 'category', None)
        if category:
            yield (DCT.type, OSF[category])

    def _gather_dates(self):
        yield (DCT.created, getattr(self.focus, 'created', None))
        yield (DCT.available, getattr(self.focus, 'embargo_end_date', None))
        last_logged = getattr(self.focus, 'last_logged', None)
        if last_logged is not None:
            yield (DCT.modified, last_logged)
        else:
            yield (DCT.modified, getattr(self.focus, 'modified', None))

        if hasattr(self.focus, 'actions'):
            submit_triggers = [
                osfworkflows.DefaultTriggers.SUBMIT.db_name,
                osfworkflows.RegistrationModerationTriggers.SUBMIT.db_name,
            ]
            approval_triggers = [
                osfworkflows.DefaultTriggers.ACCEPT.db_name,
                osfworkflows.RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name,
            ]
            action_dates = self.focus.actions.aggregate(
                # TODO: is `Min` what we want for multiple submit/accept actions?
                #       could do `Max` instead, or include all their dates
                date_submitted=Min('created', filter=Q(trigger__in=submit_triggers)),
                date_approved=Min('created', filter=Q(trigger__in=approval_triggers)),
            )
            yield (DCT.dateSubmitted, action_dates.get('date_submitted'))
            yield (DCT.dateAccepted, action_dates.get('date_approved'))
            # TODO: withdrawn?

    def _gather_license(self):
        license_record = getattr(self.focus, 'node_license', None)
        if license_record is not None:
            yield (DCT.dateCopyrighted, license_record.year)
            for copyright_holder in license_record.copyright_holders:
                yield (DCT.rightsHolder, copyright_holder)
            license = license_record.node_license  # yes, it's focus.node_license.node_license
            if license is not None and license.url:
                yield (DCT.rights, rdflib.URIRef(license.url))
                # TODO: anything for licenses that don't have a url?

    def _gather_text(self):
        yield (DCT.title, getattr(self.focus, 'title', None))
        yield (DCT.description, getattr(self.focus, 'description', None))
        # TODO: dct:language

    def _gather_keywords(self):
        if hasattr(self.focus, 'tags'):
            tag_names = (
                self.focus.tags
                .filter(system=False)
                .values_list('name', flat=True)
            )
            for tag_name in tag_names:
                yield (OSF.keyword, tag_name)

    def _gather_subjects(self):
        if hasattr(self.focus, 'subjects'):
            for subject in self.focus.subjects.all():
                # TODO: irl, not just text
                yield (DCT.subject, subject.path)
                if subject.bepress_subject:
                    yield (DCT.subject, subject.bepress_subject.path)

    def _gather_file_specifics(self):
        yield (OSF.file_name, getattr(self.focus, 'name', None)),
        yield (OSF.file_path, getattr(self.focus, 'materialized_path', None)),
        if hasattr(self.focus, 'versions'):  # quacks like BaseFileNode
            versions = self.focus.versions.all()  # TODO: if many versions, pare down?
            if not versions.exists():  # quacks like non-osfstorage BaseFileNode
                checksums = getattr(self.focus, '_hashes', {})
                for checksum_algorithm, checksum_value in checksums.items():
                    if ' ' not in checksum_algorithm:
                        yield (OSF.has_content, _checksum_urn(checksum_algorithm, checksum_value))
            else:  # quacks like OsfStorageFileNode
                for version in versions:  # expecting version to quack like FileVersion
                    version_ref = rdflib.BNode()
                    yield (DCT.hasVersion, version_ref)
                    yield (version_ref, DCT.creator, _guid_irl(version.creator))
                    yield (version_ref, DCT.created, version.created)
                    yield (version_ref, DCT.modified, version.created)
                    yield (version_ref, DCT.requires, _checksum_urn('sha-256', version.metadata['sha256']))
                    yield (version_ref, DCT.format, version.content_type)
                    yield (version_ref, DCT.extent, version.size)  # TODO: string with unit?
                    yield (version_ref, OSF.version_number, version.identifier)

    def _gather_parts(self):
        # TODO: files without guids too?
        #       (maybe only for registration files, if they don't all have guids)
        files_with_guids = (
            osfdb.BaseFileNode.active
            .filter(
                target_object_id=self.focus.id,
                target_content_type=ContentType.objects.get_for_model(self.focus),
            )
            .annotate(num_guids=Count('guids'))
            .filter(num_guids__gt=0)
        )
        for file in files_with_guids:
            yield (DCT.hasPart, _guid_irl(file))

        if hasattr(self.focus, 'children'):
            for child in self.focus.children.all():
                yield (DCT.hasPart, _guid_irl(child))  # TODO: OSF.hasChild instead?

        parent = getattr(self.focus, 'parent_node', None)
        yield (DCT.isPartOf, _guid_irl(parent))  # TODO: OSF.isChildOf instead?

    def _gather_related_items(self):
        related_article_doi = getattr(self.focus, 'article_doi', None)
        if related_article_doi:
            doi_url = f'{website_settings.DOI_URL_PREFIX}{related_article_doi}'
            yield (DCT.relation, rdflib.URIRef(doi_url))

        if isinstance(self.focus, osfdb.Registration):
            # TODO: what do with title/description/tags/etc on osf.models.Outcome?
            artifact_qs = osfdb.OutcomeArtifact.objects.for_registration(self.focus)
            for outcome_artifact in artifact_qs:
                artifact_irl = rdflib.URIRef(outcome_artifact.identifier.as_irl())
                yield (DCT.references, artifact_irl)
                yield (artifact_irl, DCT.title, outcome_artifact.title)
                yield (artifact_irl, DCT.description, outcome_artifact.description)

        primary_file = getattr(self.focus, 'primary_file', None)
        yield (DCT.requires, _guid_irl(primary_file))

    def _gather_agents(self):
        for osf_user in getattr(self.focus, 'visible_contributors', ()):
            yield (DCT.creator, _guid_irl(osf_user))
        if hasattr(self.focus, 'affiliated_institutions'):
            for osf_institution in self.focus.affiliated_institutions.all():
                yield (OSF.affiliatedInstitution, osf_institution.name)  # TODO: irl
        # TODO:
        # dct:contributor (roles)
        # osf:funder

    def _tidy_triple(self, gathered_triple):
        """for more readable `MetadataGatherer._gather_*` methods
        """
        if len(gathered_triple) == 2:  # allow omitting subject
            gathered_triple = (self.focus_irl, *gathered_triple)
        if len(gathered_triple) != 3:  # triple means three
            raise ValueError(f'{self.__class__.__name__}._tidy_triple: triple not a triple (got {gathered_triple})')
        if any((v is None or v == '') for v in gathered_triple):
            return None  # politely skipple this triple

        subj, pred, obj = gathered_triple
        return (subj, pred, self._tidy_object(obj))

    def _tidy_object(self, triple_object):
        """for more readable `MetadataGatherer._gather_*` methods
        """
        if isinstance(triple_object, datetime.datetime):
            # no need for finer granularity than date (TODO: is that wrong?)
            triple_object = triple_object.date()
        if isinstance(triple_object, datetime.date):
            # encode dates as iso8601-formatted string literals (TODO: is xsd:dateTime good?)
            triple_object = triple_object.isoformat()
        if not isinstance(triple_object, rdflib.term.Node):
            # unless already rdflib-erated, assume it's literal
            triple_object = rdflib.Literal(triple_object)
        return triple_object
