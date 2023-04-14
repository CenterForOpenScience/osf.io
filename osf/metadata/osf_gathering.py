'''gatherers of metadata from the osf database, in particular
'''
import logging

from django.contrib.contenttypes.models import ContentType
from django import db
import rdflib

from osf import models as osfdb
from osf.metadata import gather
from osf.metadata.rdfutils import (
    RDF,
    OWL,
    DCTERMS,
    FOAF,
    OSF,
    OSFIO,
    DOI,
    ORCID,
    ROR,
    checksum_iri,
    format_dcterms_extent,
    without_namespace,
)
from osf.utils import workflows as osfworkflows
from osf.utils.outcomes import ArtifactTypes
from website import settings as website_settings


logger = logging.getLogger(__name__)


##### BEGIN "public" api #####


def pls_get_magic_metadata_basket(osf_item) -> gather.Basket:
    '''for when you just want a basket of rdf metadata about a thing

    @osf_item: the thing (osf model instance or 5-ish character guid string)
    '''
    focus = OsfFocus(osf_item)
    return gather.Basket(focus)


def osfmap_for_type(rdftype_iri: str):
    try:
        return OSFMAP[rdftype_iri]
    except KeyError:
        raise ValueError(f'invalid OSFMAP type! expected one of {set(OSFMAP.keys())}, got {rdftype_iri}')


##### END "public" api #####


##### BEGIN osfmap #####
# TODO: replace these dictionaries with dctap tsv

OSF_AGENT_REFERENCE = {
    DCTERMS.identifier: None,
    DCTERMS.type: None,
    FOAF.name: None,
    OSF.affiliatedInstitution: None,
}

OSF_OBJECT_REFERENCE = {  # could reference non-osf objects too
    DCTERMS.creator: OSF_AGENT_REFERENCE,
    DCTERMS.created: None,
    DCTERMS.identifier: None,
    DCTERMS.title: None,
    DCTERMS.type: None,
    DCTERMS.publisher: None,
}

OSF_FILE_REFERENCE = {
    DCTERMS.identifier: None,
    DCTERMS.title: None,
    DCTERMS.created: None,
    DCTERMS.modified: None,
    OSF.isContainedBy: OSF_OBJECT_REFERENCE,
    OSF.fileName: None,
    OSF.filePath: None,
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
    OSF.affiliatedInstitution: None,
    OSF.funder: None,
    OSF.contains: OSF_FILE_REFERENCE,
    OSF.hasRoot: OSF_OBJECT_REFERENCE,
    OSF.keyword: None,
    OWL.sameAs: None,
}

OSF_FILEVERSION = {
    DCTERMS.created: None,
    DCTERMS.creator: OSF_AGENT_REFERENCE,
    DCTERMS.extent: None,
    DCTERMS.modified: None,
    DCTERMS.requires: None,
    DCTERMS['format']: None,
    OSF.versionNumber: None,
}

OSFMAP = {
    OSF.Project: {
        **OSF_OBJECT,
        OSF.supplements: OSF_OBJECT_REFERENCE,
    },
    OSF.ProjectComponent: {
        **OSF_OBJECT,
        OSF.supplements: OSF_OBJECT_REFERENCE,
    },
    OSF.Registration: {
        **OSF_OBJECT,
        OSF.archivedAt: None,
        OSF.hasAnalyticCodeResource: OSF_OBJECT_REFERENCE,
        OSF.hasDataResource: OSF_OBJECT_REFERENCE,
        OSF.hasMaterialsResource: OSF_OBJECT_REFERENCE,
        OSF.hasPapersResource: OSF_OBJECT_REFERENCE,
        OSF.hasSupplementalResource: OSF_OBJECT_REFERENCE,
    },
    OSF.RegistrationComponent: {
        **OSF_OBJECT,
        OSF.archivedAt: None,
        OSF.hasAnalyticCodeResource: OSF_OBJECT_REFERENCE,
        OSF.hasDataResource: OSF_OBJECT_REFERENCE,
        OSF.hasMaterialsResource: OSF_OBJECT_REFERENCE,
        OSF.hasPapersResource: OSF_OBJECT_REFERENCE,
        OSF.hasSupplementalResource: OSF_OBJECT_REFERENCE,
    },
    OSF.Preprint: {
        **OSF_OBJECT,
        OSF.isSupplementedBy: OSF_OBJECT_REFERENCE,
    },
    OSF.File: {
        DCTERMS.created: None,
        DCTERMS.description: None,
        DCTERMS.identifier: None,
        DCTERMS.language: None,
        DCTERMS.modified: None,
        DCTERMS.title: None,
        DCTERMS.type: None,
        OSF.hasFileVersion: OSF_FILEVERSION,
        OSF.isContainedBy: OSF_OBJECT_REFERENCE,
        OSF.fileName: None,
        OSF.filePath: None,
        OSF.funder: None,
        OWL.sameAs: None,
    },
    OSF.Agent: {
        DCTERMS.identifier: None,
        FOAF.name: None,
        OSF.affiliatedInstitution: None,
        OWL.sameAs: None,
    },
}

OSF_ARTIFACT_PREDICATES = {
    ArtifactTypes.ANALYTIC_CODE: OSF.hasAnalyticCodeResource,
    ArtifactTypes.DATA: OSF.hasDataResource,
    ArtifactTypes.MATERIALS: OSF.hasMaterialsResource,
    ArtifactTypes.PAPERS: OSF.hasPapersResource,
    ArtifactTypes.SUPPLEMENTS: OSF.hasSupplementalResource,
}

##### END osfmap #####


##### BEGIN osf-specific utils #####

class OsfFocus(gather.Focus):
    def __init__(self, osf_item):
        if isinstance(osf_item, str):
            osf_item = osfdb.base.coerce_guid(osf_item).referent
        super().__init__(
            iri=osf_iri(osf_item),
            rdftype=get_rdf_type(osf_item),
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
        return OSF.Agent
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
    guids_qs = getattr(focus.dbmodel, 'guids', None)
    if guids_qs is not None:
        for osfguid in guids_qs.values_list('_id', flat=True):
            osfguid_iri = osf_iri(osfguid)
            if osfguid_iri != focus.iri:
                yield (OWL.sameAs, osfguid_iri)
            yield (DCTERMS.identifier, str(osfguid_iri))
    if hasattr(focus.dbmodel, 'get_identifier_value'):
        doi = focus.dbmodel.get_identifier_value('doi')
        if doi:
            doi_iri = DOI[doi]
            yield (OWL.sameAs, doi_iri)
            yield (DCTERMS.identifier, str(doi_iri))


@gather.er(DCTERMS.type)
def gather_flexible_types(focus):
    if hasattr(focus, 'guid_metadata_record'):
        yield (DCTERMS.type, focus.guid_metadata_record.resource_type_general)


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
        # TODO: withdrawn?


@gather.er(DCTERMS.dateCopyrighted, DCTERMS.rightsHolder, DCTERMS.rights)
def gather_licensing(focus):
    license_record = getattr(focus.dbmodel, 'node_license', None)
    if license_record is not None:
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
        for subject in focus.dbmodel.subjects.all().select_related('bepress_subject'):
            # TODO: subject iri, not just text
            yield (DCTERMS.subject, subject.text)
            if subject.bepress_subject:
                yield (DCTERMS.subject, subject.bepress_subject.text)


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
            from api.base.utils import absolute_reverse as apiv2_absolute_reverse
            fileversion_iri = rdflib.URIRef(
                apiv2_absolute_reverse(
                    'files:version-detail',
                    kwargs={
                        'version': 'v2',  # api version
                        'file_id': focus.dbmodel._id,
                        'version_id': last_fileversion.identifier,
                    },
                ),
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
    yield (fileversion_iri, DCTERMS.creator, OsfFocus(fileversion.creator))
    yield (fileversion_iri, DCTERMS.created, fileversion.created)
    yield (fileversion_iri, DCTERMS.modified, fileversion.modified)
    yield (fileversion_iri, DCTERMS['format'], fileversion.content_type)
    yield (fileversion_iri, DCTERMS.extent, format_dcterms_extent(fileversion.size))
    yield (fileversion_iri, OSF.versionNumber, fileversion.identifier)
    version_sha256 = (fileversion.metadata or {}).get('sha256')
    if version_sha256:
        yield (fileversion_iri, DCTERMS.requires, checksum_iri('sha-256', version_sha256))


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
    DCTERMS.hasVersion,
    OSF.isSupplementedBy,
    focustype_iris=[OSF.Preprint],
)
def gather_preprint_related_items(focus):
    published_article_doi = getattr(focus.dbmodel, 'article_doi', None)
    if published_article_doi:
        article_iri = DOI[published_article_doi]
        yield (DCTERMS.hasVersion, article_iri)
        yield (article_iri, DCTERMS.identifier, str(article_iri))
    supplemental_node = focus.dbmodel.node
    if supplemental_node and supplemental_node.is_public:
        yield (OSF.isSupplementedBy, OsfFocus(supplemental_node))


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


@gather.er(OSF.affiliatedInstitution)
def gather_affiliated_institutions(focus):
    if hasattr(focus.dbmodel, 'get_affiliated_institutions'):   # like OSFUser
        institution_qs = focus.dbmodel.get_affiliated_institutions()
    elif hasattr(focus.dbmodel, 'affiliated_institutions'):     # like AbstractNode
        institution_qs = focus.dbmodel.affiliated_institutions.all()
    else:
        institution_qs = ()
    for osf_institution in institution_qs:
        if osf_institution.ror_uri:                 # prefer ROR if we have it
            institution_iri = rdflib.URIRef(osf_institution.ror_uri)
        elif osf_institution.identifier_domain:     # if not ROR, at least URI
            institution_iri = rdflib.URIRef(osf_institution.identifier_domain)
        else:                                       # fallback to a blank node
            institution_iri = rdflib.BNode()
        yield (OSF.affiliatedInstitution, institution_iri)
        yield (institution_iri, RDF.type, OSF.Agent)
        yield (institution_iri, DCTERMS.type, FOAF.Organization)
        yield (institution_iri, FOAF.name, osf_institution.name)
        yield (institution_iri, DCTERMS.identifier, osf_institution.ror_uri)
        yield (institution_iri, DCTERMS.identifier, osf_institution.identifier_domain)


@gather.er(OSF.funder)
def gather_funding(focus):
    if hasattr(focus, 'guid_metadata_record'):
        for funding in focus.guid_metadata_record.funding_info:
            funder_bnode = rdflib.BNode()
            yield (OSF.funder, funder_bnode)
            yield (funder_bnode, RDF.type, OSF.FundingReference)
            yield (funder_bnode, FOAF.name, funding.get('funder_name'))
            yield (funder_bnode, DCTERMS.identifier, funding.get('funder_identifier'))
            yield (funder_bnode, OSF.funderIdentifierType, funding.get('funder_identifier_type'))
            yield (funder_bnode, OSF.awardNumber, funding.get('award_number'))
            yield (funder_bnode, OSF.awardUri, funding.get('award_uri'))
            yield (funder_bnode, OSF.awardTitle, funding.get('award_title'))


@gather.er(OSF.HostingInstitution)
def gather_hosting_institution(focus):
    name = website_settings.HOSTING_INSTITUTION_NAME
    irl = website_settings.HOSTING_INSTITUTION_IRL
    ror_id = website_settings.HOSTING_INSTITUTION_ROR_ID
    if name and (irl or ror_id):
        irl_iri = rdflib.URIRef(irl) if irl else ROR[ror_id]
        yield (OSF.HostingInstitution, irl_iri)
        yield (irl_iri, RDF.type, OSF.Agent)
        yield (irl_iri, DCTERMS.type, FOAF.Organization)
        yield (irl_iri, FOAF.name, name)
        yield (irl_iri, DCTERMS.identifier, irl)
        if ror_id:
            yield (irl_iri, DCTERMS.identifier, ROR[ror_id])
    else:
        logger.warning(
            'must set website.settings.HOSTING_INSTITUTION_NAME'
            ' and either website.settings.HOSTING_INSTITUTION_IRL'
            ' or website.settings.HOSTING_INSTITUTION_ROR_ID'
            ' to include in metadata records'
        )


@gather.er(focustype_iris=[OSF.Agent])
def gather_user_basics(focus):
    if isinstance(focus.dbmodel, osfdb.OSFUser):
        yield (DCTERMS.type, FOAF.Person)
        yield (FOAF.name, focus.dbmodel.fullname)
        for social_link in focus.dbmodel.social_links.values():
            if isinstance(social_link, str):
                yield (DCTERMS.identifier, social_link)
            elif isinstance(social_link, list):
                for link in social_link:
                    yield (DCTERMS.identifier, link)
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
    yield (OSF.archivedAt, focus.dbmodel.ia_url)


@gather.er(DCTERMS.publisher)
def gather_publisher(focus):
    provider = getattr(focus.dbmodel, 'provider', None)
    if isinstance(provider, osfdb.AbstractProvider):
        if isinstance(provider, osfdb.PreprintProvider):
            provider_path_prefix = 'preprints'
        elif isinstance(provider, osfdb.RegistrationProvider):
            provider_path_prefix = 'registries'
        elif isinstance(provider, osfdb.CollectionProvider):
            provider_path_prefix = 'collections'
        else:
            raise ValueError(f'unknown provider type: {type(provider)} (for provider {provider})')
        provider_iri = OSFIO[f'{provider_path_prefix}/{provider._id}']
        yield from _publisher_tripleset(iri=provider_iri, name=provider.name, url=provider.domain)
    else:
        yield from _publisher_tripleset(
            iri=rdflib.URIRef(OSFIO.rstrip('/')),
            name='OSF',
        )


def _publisher_tripleset(iri, name, url=None):
    yield (DCTERMS.publisher, iri)
    yield (iri, RDF.type, OSF.Agent)
    yield (iri, DCTERMS.type, FOAF.Organization)
    yield (iri, FOAF.name, name)
    yield (iri, DCTERMS.identifier, str(iri))
    yield (iri, DCTERMS.identifier, url)
