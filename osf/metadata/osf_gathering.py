'''gatherers of metadata from the osf database, in particular
'''
import datetime
import enum
import logging

from django.contrib.contenttypes.models import ContentType
from django import db
import rdflib

from api.caching.tasks import get_storage_usage_total
from osf import models as osfdb
from osf.metadata import gather
from osf.metadata.rdfutils import (
    DATACITE,
    DCAT,
    DCMITYPE,
    DCTERMS,
    DOI,
    FOAF,
    ORCID,
    OSF,
    OSFIO,
    OWL,
    PROV,
    RDF,
    ROR,
    SKOS,
    checksum_iri,
    format_dcterms_extent,
    without_namespace,
    smells_like_iri,
)
from osf.metrics.reports import PublicItemUsageReport
from osf.metrics.utils import YearMonth
from osf.utils import (
    workflows as osfworkflows,
    permissions as osfpermissions,
)
from osf.utils.outcomes import ArtifactTypes
from website import settings as website_settings


logger = logging.getLogger(__name__)


##### BEGIN "public" api #####


def pls_get_magic_metadata_basket(osf_item) -> gather.Basket:
    '''for when you just want a basket of rdf metadata about a thing

    @osf_item: the thing (an instance of osf.models.base.GuidMixin or a 5-ish character osf:id string)
    '''
    focus = OsfFocus(osf_item)
    return gather.Basket(focus)


##### END "public" api #####


##### BEGIN osfmap #####
# TODO: replace these dictionaries with dctap tsv or rdf/shacl file

OSF_AGENT_REFERENCE = {
    DCTERMS.identifier: None,
    DCTERMS.type: None,
    FOAF.name: None,
    OSF.affiliation: None,
}

OSF_OBJECT_REFERENCE = {  # could reference non-osf objects too
    DCTERMS.creator: OSF_AGENT_REFERENCE,
    DCTERMS.created: None,
    DCTERMS.identifier: None,
    DCTERMS.title: None,
    DCTERMS.type: None,
    DCTERMS.publisher: None,
    DCTERMS.rights: None,
    OSF.affiliation: None,
    OSF.funder: None,
    OSF.hasFunding: None,
}

OSF_FILE_REFERENCE = {
    DCTERMS.identifier: None,
    DCTERMS.title: None,
    DCTERMS.created: None,
    DCTERMS.modified: None,
    OSF.isContainedBy: OSF_OBJECT_REFERENCE,
    OSF.fileName: None,
    OSF.filePath: None,
    OSF.hasFileVersion: None,
}

OSF_OBJECT = {
    DCTERMS.available: None,
    DCTERMS.contributor: OSF_AGENT_REFERENCE,
    DCTERMS.created: None,
    DCTERMS.creator: OSF_AGENT_REFERENCE,
    DCTERMS.dateAccepted: None,
    DCTERMS.dateCopyrighted: None,
    DCTERMS.dateSubmitted: None,
    DCTERMS.description: None,
    DCTERMS.hasPart: OSF_OBJECT_REFERENCE,
    DCTERMS.hasVersion: OSF_OBJECT_REFERENCE,
    DCTERMS.identifier: None,
    DCTERMS.isPartOf: OSF_OBJECT_REFERENCE,
    DCTERMS.isVersionOf: OSF_OBJECT_REFERENCE,
    DCTERMS.language: None,
    DCTERMS.modified: None,
    DCTERMS.publisher: OSF_AGENT_REFERENCE,
    DCTERMS.references: OSF_OBJECT_REFERENCE,
    DCTERMS.relation: OSF_OBJECT_REFERENCE,
    DCTERMS.rights: None,
    DCTERMS.rightsHolder: None,
    DCTERMS.subject: None,
    DCTERMS.title: None,
    DCTERMS.type: None,
    OSF.hostingInstitution: None,
    DCAT.accessService: None,
    OSF.affiliation: None,
    OSF.isPartOfCollection: None,
    OSF.funder: None,
    OSF.hasFunding: None,
    OSF.contains: OSF_FILE_REFERENCE,
    OSF.hasRoot: OSF_OBJECT_REFERENCE,
    OSF.keyword: None,
    OSF.dateWithdrawn: None,
    OSF.withdrawal: {
        DCTERMS.created: None,
        DCTERMS.dateAccepted: None,
        DCTERMS.description: None,
        DCTERMS.creator: OSF_AGENT_REFERENCE,
    },
    OWL.sameAs: None,
    PROV.qualifiedAttribution: None,
}

OSFMAP = {
    OSF.Project: {
        **OSF_OBJECT,
        OSF.supplements: OSF_OBJECT_REFERENCE,
        OSF.hasCedarTemplate: None,
        OSF.verifiedLink: None,
    },
    OSF.ProjectComponent: {
        **OSF_OBJECT,
        OSF.supplements: OSF_OBJECT_REFERENCE,
        OSF.hasCedarTemplate: None,
    },
    OSF.Registration: {
        **OSF_OBJECT,
        OSF.archivedAt: None,
        DCTERMS.conformsTo: None,
        OSF.hasAnalyticCodeResource: OSF_OBJECT_REFERENCE,
        OSF.hasDataResource: OSF_OBJECT_REFERENCE,
        OSF.hasMaterialsResource: OSF_OBJECT_REFERENCE,
        OSF.hasPapersResource: OSF_OBJECT_REFERENCE,
        OSF.hasSupplementalResource: OSF_OBJECT_REFERENCE,
        OSF.hasCedarTemplate: None,
    },
    OSF.RegistrationComponent: {
        **OSF_OBJECT,
        OSF.archivedAt: None,
        DCTERMS.conformsTo: None,
        OSF.hasAnalyticCodeResource: OSF_OBJECT_REFERENCE,
        OSF.hasDataResource: OSF_OBJECT_REFERENCE,
        OSF.hasMaterialsResource: OSF_OBJECT_REFERENCE,
        OSF.hasPapersResource: OSF_OBJECT_REFERENCE,
        OSF.hasSupplementalResource: OSF_OBJECT_REFERENCE,
        OSF.hasCedarTemplate: None,
    },
    OSF.Preprint: {
        **OSF_OBJECT,
        OSF.isSupplementedBy: OSF_OBJECT_REFERENCE,
        OSF.hasDataResource: None,
        OSF.hasPreregisteredStudyDesign: None,
        OSF.hasPreregisteredAnalysisPlan: None,
        OSF.statedConflictOfInterest: None,
    },
    OSF.File: {
        DCAT.accessService: None,
        DCTERMS.created: None,
        DCTERMS.description: None,
        DCTERMS.identifier: None,
        DCTERMS.language: None,
        DCTERMS.modified: None,
        DCTERMS.title: None,
        DCTERMS.type: None,
        OSF.hasFileVersion: None,
        OSF.isContainedBy: OSF_OBJECT_REFERENCE,
        OSF.fileName: None,
        OSF.filePath: None,
        OSF.funding: None,
        OSF.hasFunding: None,
        OSF.hasCedarTemplate: None,
        OWL.sameAs: None,
    },
    DCTERMS.Agent: {
        DCAT.accessService: None,
        DCTERMS.identifier: None,
        FOAF.name: None,
        OSF.affiliation: None,
        OWL.sameAs: None,
    },
}

# metadata not included in the core record
OSFMAP_SUPPLEMENT = {
    OSF.Project: {
        OSF.hasOsfAddon: None,
        OSF.storageByteCount: None,
        OSF.storageRegion: None,
    },
    OSF.ProjectComponent: {
        OSF.hasOsfAddon: None,
        OSF.storageByteCount: None,
        OSF.storageRegion: None,
    },
    OSF.Registration: {
        OSF.storageByteCount: None,
        OSF.storageRegion: None,
    },
    OSF.RegistrationComponent: {
        OSF.storageByteCount: None,
        OSF.storageRegion: None,
    },
    OSF.Preprint: {
        OSF.storageByteCount: None,
        OSF.storageRegion: None,
    },
    OSF.File: {
    },
}

# metadata not included in the core record that expires after a month
OSFMAP_MONTHLY_SUPPLEMENT = {
    OSF.Project: {
        OSF.usage: None,
    },
    OSF.ProjectComponent: {
        OSF.usage: None,
    },
    OSF.Registration: {
        OSF.usage: None,
    },
    OSF.RegistrationComponent: {
        OSF.usage: None,
    },
    OSF.Preprint: {
        OSF.usage: None,
    },
    OSF.File: {
        OSF.usage: None,
    },
}


OSF_ARTIFACT_PREDICATES = {
    ArtifactTypes.ANALYTIC_CODE: OSF.hasAnalyticCodeResource,
    ArtifactTypes.DATA: OSF.hasDataResource,
    ArtifactTypes.MATERIALS: OSF.hasMaterialsResource,
    ArtifactTypes.PAPERS: OSF.hasPapersResource,
    ArtifactTypes.SUPPLEMENTS: OSF.hasSupplementalResource,
}
OSF_CONTRIBUTOR_ROLES = {
    osfpermissions.READ: OSF['readonly-contributor'],
    osfpermissions.WRITE: OSF['write-contributor'],
    osfpermissions.ADMIN: OSF['admin-contributor'],
}

BEPRESS_SUBJECT_SCHEME_URI = 'https://bepress.com/reference_guide_dc/disciplines/'
BEPRESS_SUBJECT_SCHEME_TITLE = 'bepress Digital Commons Three-Tiered Taxonomy'

DATACITE_RESOURCE_TYPES_GENERAL = {
    'Audiovisual',
    'Book',
    'BookChapter',
    'Collection',
    'ComputationalNotebook',
    'ConferencePaper',
    'ConferenceProceeding',
    'DataPaper',
    'Dataset',
    'Dissertation',
    'Event',
    'Image',
    'Instrument',
    'InteractiveResource',
    'Journal',
    'JournalArticle',
    'Model',
    'OutputManagementPlan',
    'PeerReview',
    'PhysicalObject',
    'Preprint',
    'Report',
    'Service',
    'Software',
    'Sound',
    'Standard',
    'StudyRegistration',
    'Text',
    'Workflow',
    'Other',
}
DATACITE_RESOURCE_TYPE_BY_OSF_TYPE = {
    OSF.Preprint: 'Preprint',
    OSF.Registration: {
        'all': 'StudyRegistration',
        'dataarchive': 'Dataset'
    },
}


class OsfmapPartition(enum.Enum):
    MAIN = OSFMAP
    SUPPLEMENT = OSFMAP_SUPPLEMENT
    MONTHLY_SUPPLEMENT = OSFMAP_MONTHLY_SUPPLEMENT

    @property
    def is_supplementary(self) -> bool:
        return self is not OsfmapPartition.MAIN

    def osfmap_for_type(self, rdftype_iri: str):
        try:
            return self.value[rdftype_iri]
        except KeyError:
            if self.is_supplementary:
                return {}  # allow missing types for non-main partitions
            raise ValueError(f'invalid OSFMAP type! expected one of {set(self.value.keys())}, got {rdftype_iri}')

    def get_expiration_date(self, basket: gather.Basket) -> datetime.date | None:
        if self is not OsfmapPartition.MONTHLY_SUPPLEMENT:
            return None
        # let a monthly report expire two months after its reporting period ends
        # (this allows the *next* monthly report up to a month to compute, which
        # aligns with COUNTER https://www.countermetrics.org/code-of-practice/ )
        # (HACK: entangled with `gather_last_month_usage` implementation, below)
        _report_yearmonth_str = next(basket[OSF.usage / DCTERMS.temporal], None)
        if _report_yearmonth_str is None:
            return None
        _report_yearmonth = YearMonth.from_str(_report_yearmonth_str)
        return _report_yearmonth.next().next().month_end().date()

##### END osfmap #####


##### BEGIN osf-specific utils #####

class OsfFocus(gather.Focus):
    def __init__(self, osf_item):
        if isinstance(osf_item, str):
            osf_item = osfdb.base.coerce_guid(osf_item).referent
        super().__init__(
            iri=osf_iri(osf_item),
            rdftype=get_rdf_type(osf_item),
            provider_id=osf_item.provider._id if (osf_item and getattr(osf_item, 'type', '') == 'osf.registration' and osf_item.provider) else None
        )
        self.dbmodel = osf_item
        try:
            self.guid_metadata_record = osfdb.GuidMetadataRecord.objects.for_guid(osf_item)
        except osfdb.base.InvalidGuid:
            pass  # is ok for a focus to be something non-osfguidy


def is_root(osf_node):
    return (osf_node.root_id == osf_node.id)


def get_rdf_type(osfguid_referent):
    if isinstance(osfguid_referent, osfdb.Guid):
        osfguid_referent = osfguid_referent.referent

    if isinstance(osfguid_referent, osfdb.OSFUser):
        return DCTERMS.Agent
    if isinstance(osfguid_referent, osfdb.BaseFileNode):
        return OSF.File
    if isinstance(osfguid_referent, osfdb.Preprint):
        return OSF.Preprint
    if isinstance(osfguid_referent, osfdb.Registration):
        return (
            OSF.Registration
            if is_root(osfguid_referent)
            else OSF.RegistrationComponent
        )
    if isinstance(osfguid_referent, osfdb.Node):
        return (
            OSF.Project
            if is_root(osfguid_referent)
            else OSF.ProjectComponent
        )
    raise NotImplementedError


def osf_iri(guid_or_model):
    """return a rdflib.URIRef or None

    @param guid_or_model: a string, Guid instance, or another osf model instance
    @returns rdflib.URIRef or None
    """
    guid = osfdb.base.coerce_guid(guid_or_model)
    return OSFIO[guid._id]


def osfguid_from_iri(iri):
    if iri.startswith(OSFIO):
        return without_namespace(iri, OSFIO)
    raise ValueError(f'expected iri starting with "{OSFIO}" (got "{iri}")')


##### END osf-specific utils #####


##### BEGIN the gatherers #####
#

@gather.er(DCTERMS.identifier, rdflib.OWL.sameAs)
def gather_identifiers(focus: gather.Focus):
    try:
        _iris = focus.dbmodel.get_semantic_iris()
    except AttributeError:
        pass
    else:
        for _iri in _iris:
            if _iri != str(focus.iri):
                yield (OWL.sameAs, rdflib.URIRef(_iri))
            yield (DCTERMS.identifier, rdflib.Literal(_iri))


@gather.er(DCTERMS.type)
def gather_flexible_types(focus):
    _type_label = None
    try:
        _type_label = focus.guid_metadata_record.resource_type_general
    except AttributeError:
        pass
    if not _type_label:
        _type_label = DATACITE_RESOURCE_TYPE_BY_OSF_TYPE.get(focus.rdftype)
        if isinstance(_type_label, dict):
            _type_label = _type_label.get('dataarchive') if focus.provider_id == 'dataarchive' else _type_label.get('all')
    if _type_label in DATACITE_RESOURCE_TYPES_GENERAL:
        _type_ref = DATACITE[_type_label]
        yield (DCTERMS.type, _type_ref)
        yield (_type_ref, rdflib.RDFS.label, rdflib.Literal(_type_label, lang='en'))


@gather.er(DCTERMS.created)
def gather_created(focus):
    if focus.rdftype == OSF.Registration:
        yield (DCTERMS.created, getattr(focus.dbmodel, 'registered_date', None))
    else:
        yield (DCTERMS.created, getattr(focus.dbmodel, 'created', None))


@gather.er(DCTERMS.available)
def gather_available(focus):
    embargo = getattr(focus.dbmodel, 'embargo', None)
    if embargo:
        yield (DCTERMS.available, embargo.end_date)


@gather.er(DCTERMS.modified)
def gather_modified(focus):
    last_logged = getattr(focus.dbmodel, 'last_logged', None)
    if last_logged is not None:
        yield (DCTERMS.modified, last_logged)
    else:
        yield (DCTERMS.modified, getattr(focus.dbmodel, 'modified', None))


@gather.er(DCTERMS.dateSubmitted, DCTERMS.dateAccepted)
def gather_moderation_dates(focus):
    if hasattr(focus.dbmodel, 'actions'):
        submit_triggers = [
            osfworkflows.DefaultTriggers.SUBMIT.db_name,
            osfworkflows.RegistrationModerationTriggers.SUBMIT.db_name,
        ]
        accept_triggers = [
            osfworkflows.DefaultTriggers.ACCEPT.db_name,
            osfworkflows.RegistrationModerationTriggers.ACCEPT_SUBMISSION.db_name,
        ]
        action_dates = focus.dbmodel.actions.aggregate(
            # TODO: is `Min` what we want for multiple submit/accept actions?
            #       could do `Max` instead, or even include ALL submitted/accepted dates
            date_submitted=db.models.Min(
                'created',
                filter=db.models.Q(trigger__in=submit_triggers),
            ),
            date_accepted=db.models.Min(
                'created',
                filter=db.models.Q(trigger__in=accept_triggers),
            ),
        )
        yield (DCTERMS.dateSubmitted, action_dates.get('date_submitted'))
        yield (DCTERMS.dateAccepted, action_dates.get('date_accepted'))


@gather.er(
    OSF.dateWithdrawn,
    OSF.withdrawal,
    focustype_iris=(OSF.Registration,)
)
def gather_registration_withdrawal(focus):
    _retraction = focus.dbmodel.root.retraction
    if _retraction and _retraction.is_approved:
        yield (OSF.dateWithdrawn, _retraction.date_retracted)
        _withdrawal_ref = rdflib.BNode()
        yield (OSF.withdrawal, _withdrawal_ref)
        yield (_withdrawal_ref, RDF.type, OSF.Withdrawal)
        yield (_withdrawal_ref, DCTERMS.created, _retraction.initiation_date)
        yield (_withdrawal_ref, DCTERMS.dateAccepted, _retraction.date_retracted)
        yield (_withdrawal_ref, DCTERMS.description, _retraction.justification)
        yield (_withdrawal_ref, DCTERMS.creator, OsfFocus(_retraction.initiated_by))


@gather.er(
    OSF.dateWithdrawn,
    OSF.withdrawal,
    focustype_iris=(OSF.Preprint,)
)
def gather_preprint_withdrawal(focus):
    _preprint = focus.dbmodel
    yield (OSF.dateWithdrawn, _preprint.date_withdrawn)
    _withdrawal_request = _preprint.requests.filter(
        machine_state=osfworkflows.ReviewStates.ACCEPTED.value,
        request_type=osfworkflows.RequestTypes.WITHDRAWAL.value,
    ).last()
    if _withdrawal_request:
        _withdrawal_ref = rdflib.BNode()
        yield (OSF.withdrawal, _withdrawal_ref)
        yield (_withdrawal_ref, RDF.type, OSF.Withdrawal)
        yield (_withdrawal_ref, DCTERMS.created, _withdrawal_request.created)
        yield (_withdrawal_ref, DCTERMS.dateAccepted, _withdrawal_request.date_last_transitioned)
        yield (_withdrawal_ref, DCTERMS.description, _withdrawal_request.comment)
        yield (_withdrawal_ref, DCTERMS.creator, OsfFocus(_withdrawal_request.creator))
    elif _preprint.date_withdrawn and _preprint.withdrawal_justification:
        # no withdrawal request, but is still withdrawn
        _withdrawal_ref = rdflib.BNode()
        yield (OSF.withdrawal, _withdrawal_ref)
        yield (_withdrawal_ref, RDF.type, OSF.Withdrawal)
        yield (_withdrawal_ref, DCTERMS.created, _preprint.date_withdrawn)
        yield (_withdrawal_ref, DCTERMS.dateAccepted, _preprint.date_withdrawn)
        yield (_withdrawal_ref, DCTERMS.description, _preprint.withdrawal_justification)


@gather.er(DCTERMS.dateCopyrighted, DCTERMS.rightsHolder, DCTERMS.rights)
def gather_licensing(focus):
    yield from _rights_for_item(focus.dbmodel)


def _rights_for_item(item):
    license_record = (
        item.license
        if isinstance(item, osfdb.Preprint)
        else getattr(item, 'node_license', None)
    )
    if license_record is None:
        _parent = getattr(item, 'parent_node', None)
        if _parent:
            yield from _rights_for_item(_parent)
    else:
        yield (DCTERMS.dateCopyrighted, license_record.year)
        for copyright_holder in license_record.copyright_holders:
            yield (DCTERMS.rightsHolder, copyright_holder)
        license = license_record.node_license  # yes, it is node.node_license.node_license
        if license is not None:
            if license.url:
                license_id = rdflib.URIRef(license.url)
                yield (license_id, DCTERMS.identifier, str(license_id))
            else:
                license_id = rdflib.BNode()
            yield (DCTERMS.rights, license_id)
            yield (license_id, FOAF.name, license.name)


@gather.er(DCTERMS.title)
def gather_title(focus):
    yield (DCTERMS.title, _language_text(focus, getattr(focus.dbmodel, 'title', None)))
    if hasattr(focus, 'guid_metadata_record'):
        yield (DCTERMS.title, _language_text(focus, focus.guid_metadata_record.title))


def _language_text(focus, text):
    if not text:
        return None
    if getattr(text, 'language', None):
        return text  # already has non-empty language tag
    return rdflib.Literal(text, lang=_get_language(focus))


def _get_language(focus):
    if hasattr(focus, 'guid_metadata_record'):
        language = focus.guid_metadata_record.language
        if language:
            return language
    return None


@gather.er(DCTERMS.language)
def gather_language(focus):
    yield (DCTERMS.language, _get_language(focus))


@gather.er(DCTERMS.description)
def gather_description(focus):
    yield (DCTERMS.description, _language_text(focus, getattr(focus.dbmodel, 'description', None)))
    if hasattr(focus, 'guid_metadata_record'):
        yield (DCTERMS.description, _language_text(focus, focus.guid_metadata_record.description))


@gather.er(OSF.keyword)
def gather_keywords(focus):
    if hasattr(focus.dbmodel, 'tags'):
        tag_names = (
            focus.dbmodel.tags
            .filter(system=False)
            .values_list('name', flat=True)
        )
        for tag_name in tag_names:
            yield (OSF.keyword, tag_name)


@gather.er(DCTERMS.subject)
def gather_subjects(focus):
    if hasattr(focus.dbmodel, 'subjects'):
        for subject in focus.dbmodel.subjects.all().select_related('bepress_subject', 'parent__parent'):
            yield from _subject_triples(subject)


def _subject_triples(dbsubject, *, child_ref=None, related_ref=None):
    # agrees with osf.models.subject.Subject.get_semantic_iri
    _is_bepress = (not dbsubject.bepress_subject)
    _is_distinct_from_bepress = (dbsubject.text != dbsubject.bepress_text)
    if _is_bepress or _is_distinct_from_bepress:
        _subject_ref = rdflib.URIRef(dbsubject.get_semantic_iri())
        yield (DCTERMS.subject, _subject_ref)
        yield (_subject_ref, RDF.type, SKOS.Concept)
        yield (_subject_ref, SKOS.prefLabel, dbsubject.text)
        yield from _subject_scheme_triples(dbsubject, _subject_ref)
        if _is_distinct_from_bepress:
            yield from _subject_triples(dbsubject.bepress_subject, related_ref=_subject_ref)
        if child_ref is not None:
            yield (child_ref, SKOS.broader, _subject_ref)
        if related_ref is not None:
            yield (related_ref, SKOS.related, _subject_ref)
        if dbsubject.parent and (dbsubject != dbsubject.parent):
            yield from _subject_triples(dbsubject.parent, child_ref=_subject_ref)
    else:  # if the custom subject adds nothing of value, just include the bepress subject
        yield from _subject_triples(dbsubject.bepress_subject, child_ref=child_ref, related_ref=related_ref)


def _subject_scheme_triples(dbsubject, subject_ref):
    # if it has a bepress subject, it is not a bepress subject
    if dbsubject.bepress_subject:
        _scheme_title = dbsubject.provider.share_title or dbsubject.provider.name
        _scheme_ref = rdflib.URIRef(f'{dbsubject.provider.absolute_api_v2_url}subjects/')
    else:
        _scheme_title = BEPRESS_SUBJECT_SCHEME_TITLE
        _scheme_ref = rdflib.URIRef(BEPRESS_SUBJECT_SCHEME_URI)
    yield (subject_ref, SKOS.inScheme, _scheme_ref)
    yield (_scheme_ref, RDF.type, SKOS.ConceptScheme)
    yield (_scheme_ref, DCTERMS.title, _scheme_title)


@gather.er(focustype_iris=[OSF.File])
def gather_file_basics(focus):
    if isinstance(focus.dbmodel, osfdb.BaseFileNode):
        yield (OSF.isContainedBy, OsfFocus(focus.dbmodel.target))
        yield (OSF.fileName, getattr(focus.dbmodel, 'name', None))
        yield (OSF.filePath, getattr(focus.dbmodel, 'materialized_path', None))


@gather.er(
    OSF.hasFileVersion,
    focustype_iris=[OSF.File],
)
def gather_versions(focus):
    if hasattr(focus.dbmodel, 'versions'):  # quacks like BaseFileNode
        last_fileversion = focus.dbmodel.versions.last()  # just the last version, for now
        if last_fileversion is not None:  # quacks like OsfStorageFileNode
            fileversion_iri = rdflib.URIRef(
                f'{focus.iri}?revision={last_fileversion.identifier}'
            )
            yield (OSF.hasFileVersion, fileversion_iri)
            yield from _gather_fileversion(last_fileversion, fileversion_iri)
        else:  # quacks like non-osfstorage BaseFileNode
            checksums = getattr(focus.dbmodel, '_hashes', {})
            if checksums:
                blankversion = rdflib.BNode()
                yield (OSF.hasFileVersion, blankversion)
                for checksum_algorithm, checksum_value in checksums.items():
                    if ' ' not in checksum_algorithm:
                        yield (blankversion, DCTERMS.requires, checksum_iri(checksum_algorithm, checksum_value))


def _gather_fileversion(fileversion, fileversion_iri):
    yield (fileversion_iri, RDF.type, OSF.FileVersion)
    if fileversion.creator is not None:
        yield (fileversion_iri, DCTERMS.creator, OsfFocus(fileversion.creator))
    yield (fileversion_iri, DCTERMS.created, fileversion.created)
    yield (fileversion_iri, DCTERMS.modified, fileversion.modified)
    yield (fileversion_iri, DCTERMS['format'], fileversion.content_type)
    yield (fileversion_iri, DCTERMS.extent, format_dcterms_extent(fileversion.size))
    yield (fileversion_iri, OSF.versionNumber, fileversion.identifier)
    version_sha256 = (fileversion.metadata or {}).get('sha256')
    if version_sha256:
        yield (fileversion_iri, DCTERMS.requires, checksum_iri('sha-256', version_sha256))
    if fileversion.region is not None:
        yield from _storage_region_triples(fileversion.region, subject_ref=fileversion_iri)


@gather.er(OSF.contains)
def gather_files(focus):
    # TODO: files without osfguids too?
    #       (maybe only for registration files, if they don't all have osfguids)
    files_with_osfguids = (
        osfdb.BaseFileNode.active
        .filter(
            target_object_id=focus.dbmodel.id,
            target_content_type=ContentType.objects.get_for_model(focus.dbmodel),
        )
        .annotate(num_osfguids=db.models.Count('guids'))
        .filter(num_osfguids__gt=0)
    )
    primary_file_id = getattr(focus.dbmodel, 'primary_file_id', None)

    for file in files_with_osfguids:
        file_focus = OsfFocus(file)
        yield (OSF.contains, file_focus)
        if (primary_file_id is not None) and file.id == primary_file_id:
            yield (DCTERMS.requires, file_focus)


@gather.er(DCTERMS.hasPart, DCTERMS.isPartOf)
def gather_parts(focus):
    if isinstance(focus.dbmodel, osfdb.AbstractNode):
        if not is_root(focus.dbmodel) and focus.dbmodel.root.is_public:
            root_focus = OsfFocus(focus.dbmodel.root)
            yield (OSF.hasRoot, root_focus)
        child_relations = (
            osfdb.NodeRelation.objects
            .filter(parent=focus.dbmodel, is_node_link=False)
            .select_related('child')
        )
        for child_relation in child_relations:
            child = child_relation.child
            if child.is_public:
                yield (DCTERMS.hasPart, OsfFocus(child))
    parent = getattr(focus.dbmodel, 'parent_node', None)
    if parent is not None and parent.is_public:
        yield (DCTERMS.isPartOf, OsfFocus(parent))


@gather.er(
    OSF.isSupplementedBy,
    focustype_iris=[OSF.Preprint],
)
def gather_preprint_supplement(focus):
    supplemental_node = focus.dbmodel.node
    if supplemental_node and supplemental_node.is_public:
        yield (OSF.isSupplementedBy, OsfFocus(supplemental_node))


@gather.er(
    DCTERMS.hasVersion,
    focustype_iris=[OSF.Preprint],
)
def gather_preprint_external_links(focus):
    published_article_doi = getattr(focus.dbmodel, 'article_doi', None)
    if published_article_doi:
        article_iri = DOI[published_article_doi]
        yield (DCTERMS.hasVersion, article_iri)
        yield (article_iri, DCTERMS.identifier, str(article_iri))


@gather.er(
    OSF.hasDataResource,
    focustype_iris=[OSF.Preprint],
)
def gather_preprint_data_links(focus):
    preprint = focus.dbmodel
    if preprint.has_data_links == 'no':
        yield from _omitted_metadata(
            focus=focus,
            omitted_property_set=[OSF.hasDataResource],
            description=preprint.why_no_data,
        )
    elif preprint.has_data_links == 'available':
        for data_link in filter(None, preprint.data_links):
            yield (OSF.hasDataResource, rdflib.URIRef(data_link))


@gather.er(
    OSF.hasPreregisteredStudyDesign,
    OSF.hasPreregisteredAnalysisPlan,
    focustype_iris=[OSF.Preprint],
)
def gather_preprint_prereg(focus):
    preprint = focus.dbmodel
    if preprint.has_prereg_links == 'no':
        yield from _omitted_metadata(
            focus=focus,
            omitted_property_set=[
                OSF.hasPreregisteredStudyDesign,
                OSF.hasPreregisteredAnalysisPlan,
            ],
            description=preprint.why_no_prereg,
        )
    elif preprint.has_prereg_links == 'available':
        try:
            prereg_relations = {
                'prereg_designs': [OSF.hasPreregisteredStudyDesign],
                'prereg_analysis': [OSF.hasPreregisteredAnalysisPlan],
                'prereg_both': [OSF.hasPreregisteredStudyDesign, OSF.hasPreregisteredAnalysisPlan],
            }[preprint.prereg_link_info]
        except KeyError:
            pass
        else:
            for prereg_link in filter(None, preprint.prereg_links):
                for prereg_relation in prereg_relations:
                    yield (prereg_relation, rdflib.URIRef(prereg_link))


@gather.er(
    OSF.statedConflictOfInterest,
    focustype_iris=[OSF.Preprint],
)
def gather_conflict_of_interest(focus):
    if focus.dbmodel.has_coi:
        yield (OSF.statedConflictOfInterest, _language_text(focus, focus.dbmodel.conflict_of_interest_statement))
    else:
        yield (OSF.statedConflictOfInterest, OSF['no-conflict-of-interest'])


@gather.er(
    DCTERMS.references,
    focustype_iris=[OSF.Project, OSF.ProjectComponent, OSF.Registration, OSF.RegistrationComponent]
)
def gather_node_links(focus):
    node_links = (
        osfdb.NodeRelation.objects
        .filter(parent=focus.dbmodel, is_node_link=True)
        .select_related('child')
    )
    for node_link in node_links:
        linked_node = node_link.child
        if linked_node.is_public:
            yield (DCTERMS.references, OsfFocus(linked_node))


@gather.er(
    DCTERMS.hasVersion,
    OSF.supplements,
    focustype_iris=[OSF.Project, OSF.ProjectComponent],
)
def gather_project_related_items(focus):
    for registration in focus.dbmodel.registrations.all():
        if registration.is_public:
            yield (DCTERMS.hasVersion, OsfFocus(registration))
    for preprint in focus.dbmodel.preprints.all():
        if preprint.verified_publishable:
            yield (OSF.supplements, OsfFocus(preprint))


@gather.er(
    DCTERMS.references,
    DCTERMS.isVersionOf,
    DCTERMS.relation,
    *OSF_ARTIFACT_PREDICATES.values(),
    focustype_iris=[OSF.Registration, OSF.RegistrationComponent],
)
def gather_registration_related_items(focus):
    related_article_doi = getattr(focus.dbmodel, 'article_doi', None)
    if related_article_doi:
        article_iri = DOI[related_article_doi]
        yield (DCTERMS.relation, article_iri)
        yield (article_iri, DCTERMS.identifier, str(article_iri))
    yield (DCTERMS.isVersionOf, OsfFocus(focus.dbmodel.registered_from))
    # TODO: should the title/description/tags/etc fields on osf.models.Outcome
    #       overwrite the same fields on osf.models.Registration?
    artifact_qs = (
        osfdb.OutcomeArtifact.objects
        .for_registration(focus.dbmodel)
        .filter(
            finalized=True,
            deleted__isnull=True
        )
    )
    for outcome_artifact in artifact_qs:
        should_include_artifact = (
            outcome_artifact.identifier.category == 'doi'
            and outcome_artifact.artifact_type in OSF_ARTIFACT_PREDICATES
        )
        if should_include_artifact:
            artifact_iri = DOI[outcome_artifact.identifier.value]
            yield (OSF_ARTIFACT_PREDICATES[outcome_artifact.artifact_type], artifact_iri)
            yield (artifact_iri, DCTERMS.identifier, str(artifact_iri))
            yield (artifact_iri, DCTERMS.title, _language_text(focus, outcome_artifact.title))
            yield (artifact_iri, DCTERMS.description, _language_text(focus, outcome_artifact.description))


@gather.er(DCTERMS.creator)
def gather_agents(focus):
    # TODO: contributor roles
    for user in getattr(focus.dbmodel, 'visible_contributors', ()):
        yield (DCTERMS.creator, OsfFocus(user))
    # TODO: preserve order via rdflib.Seq


@gather.er(PROV.qualifiedAttribution)
def gather_qualified_attributions(focus):
    _contributor_set = getattr(focus.dbmodel, 'contributor_set', None)
    if _contributor_set is not None:
        for index, _contributor in enumerate(_contributor_set.filter(visible=True).select_related('user')):
            _osfrole_ref = OSF_CONTRIBUTOR_ROLES.get(_contributor.permission)
            if _osfrole_ref is not None:
                _attribution_ref = rdflib.BNode()
                yield (PROV.qualifiedAttribution, _attribution_ref)
                yield (_attribution_ref, PROV.agent, OsfFocus(_contributor.user))
                yield (_attribution_ref, DCAT.hadRole, _osfrole_ref)
                yield (_attribution_ref, OSF.order, index)

@gather.er(OSF.verifiedLink)
def gather_verified_link(focus):
    links = focus.dbmodel.get_verified_links()
    for link in links:
        ref = rdflib.BNode()
        yield (OSF.verifiedLink, ref)
        yield (ref, DCAT.accessURL, link['target_url'])
        yield (ref, DATACITE.resourceTypeGeneral, link['resource_type'])

@gather.er(OSF.affiliation)
def gather_affiliated_institutions(focus):
    if hasattr(focus.dbmodel, 'get_affiliated_institutions'):   # like OSFUser
        institution_qs = focus.dbmodel.get_affiliated_institutions()
    elif hasattr(focus.dbmodel, 'affiliated_institutions'):     # like AbstractNode or Preprint
        institution_qs = focus.dbmodel.affiliated_institutions.all()
    else:
        institution_qs = ()
    for osf_institution in institution_qs:
        institution_iri = rdflib.URIRef(osf_institution.get_semantic_iri())
        yield (OSF.affiliation, institution_iri)
        yield (institution_iri, RDF.type, DCTERMS.Agent)
        yield (institution_iri, RDF.type, FOAF.Organization)
        yield (institution_iri, FOAF.name, osf_institution.name)
        yield (institution_iri, DCTERMS.identifier, osf_institution.ror_uri)
        yield (institution_iri, DCTERMS.identifier, osf_institution.identifier_domain)


@gather.er(OSF.funder, OSF.hasFunding)
def gather_funding(focus):
    if hasattr(focus, 'guid_metadata_record'):
        for _funding in focus.guid_metadata_record.funding_info:
            _funder_uri = _funding.get('funder_identifier')
            _funder_name = _funding.get('funder_name')
            _funder_ref = None
            if _funder_uri or _funder_name:
                _funder_ref = (
                    rdflib.URIRef(_funder_uri)
                    if _funder_uri
                    else rdflib.BNode()
                )
                yield (OSF.funder, _funder_ref)
                yield (_funder_ref, RDF.type, DCTERMS.Agent)
                yield (_funder_ref, DCTERMS.identifier, _funder_uri)
                yield (_funder_ref, FOAF.name, _funder_name)
            _award_uri = _funding.get('award_uri')
            _award_title = _funding.get('award_title')
            _award_number = _funding.get('award_number')
            if _award_uri or _award_title or _award_number:
                _award_ref = (
                    rdflib.URIRef(_award_uri)
                    if _award_uri
                    else rdflib.BNode()
                )
                yield (OSF.hasFunding, _award_ref)
                yield (_award_ref, RDF.type, OSF.FundingAward)
                yield (_award_ref, DCTERMS.identifier, _award_uri)
                yield (_award_ref, DCTERMS.title, _award_title)
                yield (_award_ref, OSF.awardNumber, _award_number)
                if _funder_ref:
                    yield (_award_ref, DCTERMS.contributor, _funder_ref)


@gather.er(DCAT.accessService)
def gather_access_service(focus):
    yield (DCAT.accessService, rdflib.URIRef(website_settings.DOMAIN.rstrip('/')))


@gather.er(OSF.hostingInstitution)
def gather_hosting_institution(focus):
    name = website_settings.HOSTING_INSTITUTION_NAME
    irl = website_settings.HOSTING_INSTITUTION_IRL
    ror_id = website_settings.HOSTING_INSTITUTION_ROR_ID
    if name and (irl or ror_id):
        irl_iri = rdflib.URIRef(irl) if irl else ROR[ror_id]
        yield (OSF.hostingInstitution, irl_iri)
        yield (irl_iri, RDF.type, DCTERMS.Agent)
        yield (irl_iri, RDF.type, FOAF.Organization)
        yield (irl_iri, FOAF.name, name)
        yield (irl_iri, DCTERMS.identifier, irl)
        if ror_id:
            ror_iri = ROR[ror_id]
            yield (irl_iri, DCTERMS.identifier, str(ror_iri))
            if ror_iri != irl_iri:
                yield (irl_iri, OWL.sameAs, ror_iri)
    else:
        logger.warning(
            'must set website.settings.HOSTING_INSTITUTION_NAME'
            ' and either website.settings.HOSTING_INSTITUTION_IRL'
            ' or website.settings.HOSTING_INSTITUTION_ROR_ID'
            ' to include in metadata records'
        )


@gather.er(focustype_iris=[DCTERMS.Agent])
def gather_user_basics(focus):
    if isinstance(focus.dbmodel, osfdb.OSFUser):
        yield (RDF.type, FOAF.Person)  # note: assumes osf user accounts represent people
        yield (FOAF.name, focus.dbmodel.fullname)
        _social_links = focus.dbmodel.social_links
        # special cases abound! do these one-by-one (based on OSFUser.SOCIAL_FIELDS)
        yield (DCTERMS.identifier, _social_links.get('github'))
        yield (DCTERMS.identifier, _social_links.get('scholar'))
        yield (DCTERMS.identifier, _social_links.get('linkedIn'))
        yield (DCTERMS.identifier, _social_links.get('impactStory'))
        yield (DCTERMS.identifier, _social_links.get('researcherId'))
        yield (DCTERMS.identifier, _social_links.get('researchGate'))
        yield (DCTERMS.identifier, _social_links.get('baiduScholar'))
        yield (DCTERMS.identifier, _social_links.get('ssrn'))
        for _url in _social_links.get('profileWebsites', ()):
            yield (DCTERMS.identifier, _url)
        _academia_institution = _social_links.get('academiaInstitution')
        _academia_profile_id = _social_links.get('academiaProfileID')
        if _academia_institution and _academia_profile_id:
            yield (DCTERMS.identifier, ''.join((_academia_institution, _academia_profile_id)))
        orcid = focus.dbmodel.get_verified_external_id('ORCID', verified_only=True)
        if orcid:
            orcid_iri = ORCID[orcid]
            yield (OWL.sameAs, orcid_iri)
            yield (DCTERMS.identifier, str(orcid_iri))


@gather.er(
    OSF.archivedAt,
    focustype_iris=[OSF.Registration]
)
def gather_ia_url(focus):
    if smells_like_iri(focus.dbmodel.ia_url):
        yield (OSF.archivedAt, rdflib.URIRef(focus.dbmodel.ia_url))


@gather.er(
    DCTERMS.conformsTo,
    focustype_iris=[OSF.Registration, OSF.RegistrationComponent]
)
def gather_registration_type(focus):
    _reg_schema = getattr(focus.dbmodel.root, 'registration_schema')
    if _reg_schema:
        # using iri for the earliest schema version, so later versions are recognized as the same
        # (TODO-someday: commit to a web-friendly schema url that resolves to something helpful)
        _earliest_schema_version = osfdb.RegistrationSchema.objects.get_earliest_version(_reg_schema.name)
        _schema_url = rdflib.URIRef(_earliest_schema_version.absolute_api_v2_url)
        yield (DCTERMS.conformsTo, _schema_url)
        yield (_schema_url, DCTERMS.title, _reg_schema.name)
        yield (_schema_url, DCTERMS.description, _reg_schema.description)


@gather.er(DCTERMS.publisher)
def gather_publisher(focus):
    provider = getattr(focus.dbmodel, 'provider', None)
    if isinstance(provider, osfdb.AbstractProvider):
        yield from _publisher_tripleset(
            iri=rdflib.URIRef(provider.get_semantic_iri()),
            name=provider.name,
            url=provider.domain,
        )
    else:
        yield from _publisher_tripleset(
            iri=rdflib.URIRef(OSFIO.rstrip('/')),
            name='OSF',
        )


@gather.er(OSF.isPartOfCollection)
def gather_collection_membership(focus):
    try:
        _guids = focus.dbmodel.guids.all()
    except AttributeError:
        return  # no guids
    _collection_submissions = (
        osfdb.CollectionSubmission.objects
        .filter(
            guid__in=_guids,
            machine_state=osfworkflows.CollectionSubmissionStates.ACCEPTED,
            collection__provider__isnull=False,
            collection__deleted__isnull=True,
            collection__is_bookmark_collection=False,
        )
        .select_related('collection__provider')
    )
    for _submission in _collection_submissions:
        # note: in current use, there's only one collection per provider and the
        # provider name is used as collection title (while collection.title is
        # auto-generated and ignored)
        _provider = _submission.collection.provider
        _collection_ref = rdflib.URIRef(
            f'{website_settings.DOMAIN}collections/{_provider._id}',
        )
        yield (OSF.isPartOfCollection, _collection_ref)
        yield (_collection_ref, DCTERMS.type, DCMITYPE.Collection)
        yield (_collection_ref, DCTERMS.title, _provider.name)


def _publisher_tripleset(iri, name, url=None):
    yield (DCTERMS.publisher, iri)
    yield (iri, RDF.type, DCTERMS.Agent)
    yield (iri, RDF.type, FOAF.Organization)
    yield (iri, FOAF.name, name)
    yield (iri, DCTERMS.identifier, str(iri))
    yield (iri, DCTERMS.identifier, url)


def _omitted_metadata(focus, omitted_property_set, description):
    bnode = rdflib.BNode()
    yield (focus.iri, OSF.omits, bnode)
    for property_iri in omitted_property_set:
        yield (bnode, OSF.omittedMetadataProperty, property_iri)
    yield (bnode, DCTERMS.description, _language_text(focus, description))

@gather.er(OSF.hasCedarTemplate)
def gather_cedar_templates(focus):
    try:
        _guids = focus.dbmodel.guids.all()
    except AttributeError:
        return  # no guids
    records = osfdb.CedarMetadataRecord.objects.filter(guid__in=_guids, is_published=True)
    for record in records:
        template_iri = rdflib.URIRef(record.get_template_semantic_iri())
        yield (OSF.hasCedarTemplate, template_iri)
        yield (template_iri, DCTERMS.title, record.get_template_name())


@gather.er(OSF.usage)
def gather_last_month_usage(focus):
    _usage_report = PublicItemUsageReport.for_last_month(
        item_osfid=osfguid_from_iri(focus.iri),
    )
    if _usage_report is not None:
        _usage_report_ref = rdflib.BNode()
        yield (OSF.usage, _usage_report_ref)
        yield (_usage_report_ref, DCAT.accessService, rdflib.URIRef(website_settings.DOMAIN.rstrip('/')))
        yield (_usage_report_ref, FOAF.primaryTopic, focus.iri)
        yield (_usage_report_ref, DCTERMS.temporal, rdflib.Literal(
            str(_usage_report.report_yearmonth),
            datatype=rdflib.XSD.gYearMonth,
        ))
        yield (_usage_report_ref, OSF.viewCount, _usage_report.view_count)
        yield (_usage_report_ref, OSF.viewSessionCount, _usage_report.view_session_count)
        yield (_usage_report_ref, OSF.downloadCount, _usage_report.download_count)
        yield (_usage_report_ref, OSF.downloadSessionCount, _usage_report.download_session_count)


@gather.er(OSF.hasOsfAddon)
def gather_addons(focus):
    # note: when gravyvalet exists, use `iterate_addons_for_resource`
    # from osf.external.gravy_valet.request_helpers and get urls like
    # "https://addons.osf.example/v1/addon-imps/..." instead of a urn
    for _addon_settings in focus.dbmodel.get_addons():
        if not _addon_settings.config.added_default:  # skip always-on addons
            _addon_ref = rdflib.URIRef(f'urn:osf.io:addons:{_addon_settings.short_name}')
            yield (OSF.hasOsfAddon, _addon_ref)
            yield (_addon_ref, RDF.type, OSF.AddonImplementation)
            yield (_addon_ref, DCTERMS.identifier, _addon_settings.short_name)
            yield (_addon_ref, SKOS.prefLabel, _addon_settings.config.full_name)


@gather.er(OSF.storageRegion)
def gather_storage_region(focus):
    _region = getattr(focus.dbmodel, 'osfstorage_region', None)
    if _region is not None:
        yield from _storage_region_triples(_region)


def _storage_region_triples(region, *, subject_ref=None):
    _region_ref = rdflib.URIRef(region.absolute_api_v2_url)
    if subject_ref is None:
        yield (OSF.storageRegion, _region_ref)
    else:
        yield (subject_ref, OSF.storageRegion, _region_ref)
    yield (_region_ref, SKOS.prefLabel, rdflib.Literal(region.name, lang='en'))


@gather.er(
    OSF.storageByteCount,
    focustype_iris=[OSF.Project, OSF.ProjectComponent, OSF.Registration, OSF.RegistrationComponent, OSF.Preprint]
)
def gather_storage_byte_count(focus):
    _storage_usage_total = get_storage_usage_total(focus.dbmodel)
    if _storage_usage_total is not None:
        yield (OSF.storageByteCount, _storage_usage_total)
