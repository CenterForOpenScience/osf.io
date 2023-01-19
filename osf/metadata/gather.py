import datetime
import itertools

import rdflib

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Min, Q

from osf import models as osfdb
from osf.metadata import rdfutils
from osf.utils import workflows as osfworkflows

from website import settings as website_settings


__all__ = ('gather_osfguid_metadata',)


OSF = rdfutils.OSF
DCT = rdflib.DCTERMS
FOAF = rdflib.FOAF
A = rdflib.RDF.type
SAME_AS = rdflib.OWL.sameAs


def gather_osfguid_metadata(guid: str, max_guids: int = 1) -> rdflib.Graph:
    """gather metadata about the guid's referent and related guid-items

    @param guid: osf guid (the five-ish character string)
    @param max_guids: maximum number of guids to visit (default 1, for a sparse record)
    @returns rdflib.Graph
    """
    assert isinstance(guid, str)
    guids_visited = set()
    guids_to_visit = set((guid,))
    rdf_graph = rdfutils.contextualized_graph()
    while (guids_to_visit and len(guids_visited) < max_guids):
        guid = guids_to_visit.pop()
        if guid in guids_visited:
            continue
        guids_visited.add(guid)
        gatherer = MetadataGatherer(guid)
        for triple in gatherer.gather_triples():
            rdf_graph.add(triple)
            (_, _, triple_object) = triple
            obj_guid = rdfutils.try_osfguid_from_uri(triple_object)
            if obj_guid:
                guids_to_visit.add(obj_guid)
    return rdf_graph


def _format_size_as_megabytes(number_of_bytes: int):
    # following the dcterms:extent recommendation to specify in megabytes
    # https://www.dublincore.org/specifications/dublin-core/dcmi-terms/terms/extent/
    if number_of_bytes is None or number_of_bytes < 0:
        return None
    number_of_megabytes = number_of_bytes / (2**20)
    return f'{number_of_megabytes} MB'

class MetadataGatherer:
    """for gathering metadata about a specific guid-identified object
    """
    def __init__(self, guid):
        if isinstance(guid, osfdb.Guid):
            self._guid = guid
        else:
            if '/' in guid:
                guid_id = rdfutils.try_osfguid_from_uri(guid)
            else:
                guid_id = guid
            self._guid = osfdb.Guid.load(guid_id)

        # TODO: consider optimizing with select_related and prefetch_related
        self.focus = self._guid.referent  # the "focus" is what to gather metadata about.
        self.focus_uri = rdfutils.osfguid_uri(self._guid)

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
            self._gather_custom_metadata(),
        )
        tidy_triples = map(self._tidy_triple, all_triples)
        yield from filter(None, tidy_triples)

    def _gather_identifiers(self):
        for guid in self.focus.guids.all().values_list('_id', flat=True):
            guid_uri = rdfutils.osfguid_uri(guid)
            yield (SAME_AS, guid_uri)
            yield (DCT.identifier, str(guid_uri))

        if hasattr(self.focus, 'get_identifier_uri'):
            doi_uri = self.focus.get_identifier_uri('doi')
            if doi_uri:
                yield (SAME_AS, rdflib.URIRef(doi_uri))
                yield (DCT.identifier, doi_uri)

    def _gather_types(self):
        yield (A, self._rdf_type(self.focus))
        # TODO: map category explicitly
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
            accept_triggers = [
                osfworkflows.DefaultTriggers.ACCEPT.db_name,
                osfworkflows.RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name,
            ]
            action_dates = self.focus.actions.aggregate(
                # TODO: is `Min` what we want for multiple submit/accept actions?
                #       could do `Max` instead, or include all their dates
                date_submitted=Min('created', filter=Q(trigger__in=submit_triggers)),
                date_accepted=Min('created', filter=Q(trigger__in=accept_triggers)),
            )
            yield (DCT.dateSubmitted, action_dates.get('date_submitted'))
            yield (DCT.dateAccepted, action_dates.get('date_accepted'))
            # TODO: withdrawn?

    def _gather_license(self):
        license_record = getattr(self.focus, 'node_license', None)
        if license_record is not None:
            yield (DCT.dateCopyrighted, license_record.year)
            for copyright_holder in license_record.copyright_holders:
                yield (DCT.rightsHolder, copyright_holder)
            license = license_record.node_license  # yes, it is node.node_license.node_license
            if license is not None and license.url:
                yield (DCT.rights, rdflib.URIRef(license.url))
                # TODO: anything for licenses that don't have a url?

    def _gather_text(self):
        yield (DCT.title, getattr(self.focus, 'title', None))
        yield (DCT.description, getattr(self.focus, 'description', None))

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
                # TODO: uri, not just text
                yield (DCT.subject, subject.path)
                if subject.bepress_subject:
                    yield (DCT.subject, subject.bepress_subject.path)

    def _gather_file_specifics(self):
        yield (OSF.file_name, getattr(self.focus, 'name', None))
        yield (OSF.file_path, getattr(self.focus, 'materialized_path', None))
        if hasattr(self.focus, 'versions'):  # quacks like BaseFileNode
            versions = self.focus.versions.all()  # TODO: if many versions, pare down?
            if not versions.exists():  # quacks like non-osfstorage BaseFileNode
                checksums = getattr(self.focus, '_hashes', {})
                for checksum_algorithm, checksum_value in checksums.items():
                    if ' ' not in checksum_algorithm:
                        yield (OSF.has_content, rdfutils.checksum_urn(checksum_algorithm, checksum_value))
            else:  # quacks like OsfStorageFileNode
                for version in versions:  # expecting version to quack like FileVersion
                    version_ref = rdflib.BNode()
                    yield (DCT.hasVersion, version_ref)
                    yield from self._related_guid(
                        (version_ref, DCT.creator, version.creator),
                    )
                    yield (version_ref, DCT.created, version.created)
                    yield (version_ref, DCT.modified, version.created)
                    yield (version_ref, DCT.requires, rdfutils.checksum_urn('sha-256', version.metadata['sha256']))
                    yield (version_ref, DCT.format, version.content_type)
                    yield (version_ref, DCT.extent, _format_size_as_megabytes(version.size))
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
            yield from self._related_guid((DCT.hasPart, file))

        if hasattr(self.focus, 'children'):
            for child in self.focus.children.all():
                yield from self._related_guid((DCT.hasPart, child))  # TODO: OSF.hasChild instead?

        parent = getattr(self.focus, 'parent_node', None)
        yield from self._related_guid((DCT.isPartOf, parent))  # TODO: OSF.isChildOf instead?

    def _gather_related_items(self):
        related_article_doi = getattr(self.focus, 'article_doi', None)
        if related_article_doi:
            doi_url = f'{website_settings.DOI_URL_PREFIX}{related_article_doi}'
            yield (DCT.relation, rdflib.URIRef(doi_url))

        if isinstance(self.focus, osfdb.Registration):
            # TODO: should the title/description/tags/etc fields on osf.models.Outcome
            #       overwrite the same fields on osf.models.Registration?
            artifact_qs = osfdb.OutcomeArtifact.objects.for_registration(self.focus)
            for outcome_artifact in artifact_qs:
                artifact_uri = rdflib.URIRef(outcome_artifact.identifier.as_uri())
                yield (DCT.references, artifact_uri)
                yield (artifact_uri, DCT.title, outcome_artifact.title)
                yield (artifact_uri, DCT.description, outcome_artifact.description)

        primary_file = getattr(self.focus, 'primary_file', None)
        yield from self._related_guid((DCT.requires, primary_file))

        container = getattr(self.focus, 'target', None)
        yield from self._related_guid((DCT.isPartOf, container))

    def _gather_agents(self):
        for osf_user in getattr(self.focus, 'visible_contributors', ()):
            yield from self._related_user(DCT.creator, osf_user)
        # TODO: dct:contributor (roles)
        if hasattr(self.focus, 'affiliated_institutions'):
            for osf_institution in self.focus.affiliated_institutions.all():
                yield (OSF.affiliatedInstitution, osf_institution.name)  # TODO: uri

    def _gather_custom_metadata(self):
        try:
            metadata_record = self._guid.metadata_record
        except osfdb.GuidMetadataRecord.DoesNotExist:
            pass
        else:
            yield (DCT.title, metadata_record.title)
            yield (DCT.description, metadata_record.description)
            yield (DCT.language, metadata_record.language)
            yield (DCT.type, metadata_record.resource_type_general)
            for funding in metadata_record.funding_info:
                funder_bnode = rdflib.BNode()
                yield (OSF.funder, funder_bnode)
                yield (funder_bnode, FOAF.name, funding['funder_name'])
                yield (funder_bnode, DCT.identifier, funding['funder_identifier'])
                yield (funder_bnode, OSF.award_number, funding['award_number'])
                yield (funder_bnode, OSF.award_uri, funding['award_uri'])
                yield (funder_bnode, OSF.award_title, funding['award_title'])

    def _rdf_type(self, guid_referent):
        # TODO: use rdf classes built from OSF-MAP shapes
        return OSF[guid_referent.__class__.__name__]

    def _related_user(self, predicate_uri, osf_user):
        user_uri = rdfutils.osfguid_uri(osf_user)
        yield (predicate_uri, user_uri)
        yield (user_uri, FOAF.name, osf_user.fullname)
        for social_link in osf_user.social_links.values():
            yield (user_uri, SAME_AS, rdflib.URIRef(social_link))

    def _related_guid(self, triple):
        """convenience for related guid-items
        """
        triple_start = triple[:-1]  # accept either a threeple or a shorthand twople
        related_object = triple[-1]  # object of the triple assumed to be a guid referent
        related_ref = rdfutils.osfguid_uri(related_object)
        if related_ref:
            yield (*triple_start, related_ref)  # the given triple with object swapped for URIRef
            yield (related_ref, A, self._rdf_type(related_object))  # type for the related thing

    def _tidy_triple(self, gathered_triple):
        """for more readable `MetadataGatherer._gather_*` methods
        """
        if len(gathered_triple) == 2:  # allow omitting subject
            gathered_triple = (self.focus_uri, *gathered_triple)
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
