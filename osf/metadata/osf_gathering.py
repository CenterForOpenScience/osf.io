'''gatherers of metadata from the osf database, in particular
'''
import typing

from django.contrib.contenttypes.models import ContentType
from django import db
import rdflib

from osf import exceptions
from osf import models as osfdb
from osf.metadata import gather
from osf.metadata.rdfutils import (
    RDF,
    OWL,
    DCT,
    FOAF,
    OSF,
    OSFIO,
    DOI,
    ORCID,
    checksum_iri,
    format_dct_extent,
)
from osf.metadata.serializers import METADATA_SERIALIZERS
from osf.utils import workflows as osfworkflows
from osf.utils.outcomes import ArtifactTypes


##### BEGIN "public" api #####

class SerializedMetadataFile(typing.NamedTuple):
    mediatype: str
    filename: str
    serialized_metadata: str


def pls_gather_metadata_file(osf_item, format_key, serializer_config=None) -> SerializedMetadataFile:
    '''for when you don't care about rdf or gatherbaskets, just want metadata about a thing

    @osf_item: the thing (osf model instance or 5-ish character guid string)
    @format_key: str (must be in .serializers.METADATA_SERIALIZERS)
    @serializer_config: optional dict (use only when you know the serializer will understand)
    '''
    try:
        serializer_class = METADATA_SERIALIZERS[format_key]
    except KeyError:
        valid_formats = ', '.join(METADATA_SERIALIZERS.keys())
        raise exceptions.InvalidMetadataFormat(format_key, valid_formats)
    else:
        serializer = serializer_class(serializer_config)
        osfguid = osfdb.base.coerce_guid(osf_item, create_if_needed=True)
        basket = pls_gather_item_metadata(osfguid.referent)
        return SerializedMetadataFile(
            serializer.mediatype,
            serializer.filename(osfguid._id),
            serializer.serialize(basket),
        )

def pls_gather_item_metadata(osf_item) -> gather.Basket:
    '''for when you just want a basket of rdf metadata about a thing

    @osf_item: the thing (osf model instance or 5-ish character guid string)
    '''
    focus = OsfFocus(osf_item)
    if focus.rdftype == OSF.File:
        predicate_map = OSF_FILE_METADATA
    elif focus.rdftype in (OSF.Project, OSF.Component, OSF.Preprint, OSF.Registration, OSF.RegistrationComponent):
        predicate_map = OSF_NODELIKE_METADATA
    else:
        predicate_map = OSF_COMMON_METADATA
    basket = gather.Basket(focus)
    basket.pls_gather(predicate_map)
    return basket


##### END "public" api #####


##### BEGIN osfmap #####

OSF_AGENT_REFERENCE = {
    DCT.identifier: None,
    FOAF.name: None,
    OSF.affiliated_institution: None,
}

OSF_COMMON_METADATA = {
    DCT.identifier: None,
    OWL.sameAs: None,
    DCT.type: None,
    DCT.title: None,
    DCT.description: None,
    DCT.created: None,
    DCT.available: None,
    DCT.modified: None,
    DCT.dateSubmitted: None,
    DCT.dateAccepted: None,
    DCT.dateCopyrighted: None,
    DCT.creator: OSF_AGENT_REFERENCE,
    DCT.contributor: OSF_AGENT_REFERENCE,
    DCT.language: None,
    DCT.relation: None,
    DCT.rightsHolder: None,
    DCT.rights: None,
    DCT.subject: None,
    OSF.keyword: None,
    OSF.affiliated_institution: None,
    OSF.funder: None,
}

OSF_FILE_METADATA = {
    **OSF_COMMON_METADATA,
    DCT.hasVersion: {
        DCT.creator: OSF_AGENT_REFERENCE,
    },
    OSF.file_name: None,
    OSF.file_path: None,
    DCT.isPartOf: OSF_COMMON_METADATA,
}

OSF_NODELIKE_METADATA = {
    **OSF_COMMON_METADATA,
    DCT.isPartOf: OSF_COMMON_METADATA,
    DCT.hasPart: OSF_COMMON_METADATA,
}

OSF_ARTIFACT_PREDICATES = {
    ArtifactTypes.DATA: OSF.data_resource,
    ArtifactTypes.ANALYTIC_CODE: OSF.analytic_code_resource,
    ArtifactTypes.MATERIALS: OSF.materials_resource,
    ArtifactTypes.PAPERS: OSF.papers_resource,
    ArtifactTypes.SUPPLEMENTS: OSF.supplements_resource,
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
        return OSF.OSFUser
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
            else OSF.Component
        )
    raise NotImplementedError


def osf_iri(guid_or_model):
    """return a rdflib.URIRef or None

    @param guid_or_model: a string, Guid instance, or another osf model instance
    @returns rdflib.URIRef or None
    """
    guid = osfdb.base.coerce_guid(guid_or_model)
    return OSFIO[guid._id]

##### END osf-specific utils #####


##### BEGIN the gatherers #####
#

@gather.er(DCT.identifier, rdflib.OWL.sameAs)
def gather_identifiers(focus: gather.Focus):
    guids_qs = getattr(focus.dbmodel, 'guids', None)
    if guids_qs is not None:
        for osfguid in guids_qs.values_list('_id', flat=True):
            osfguid_iri = osf_iri(osfguid)
            if osfguid_iri != focus.iri:
                yield (OWL.sameAs, osfguid_iri)
            yield (DCT.identifier, str(osfguid_iri))

    if hasattr(focus.dbmodel, 'get_identifier_value'):
        doi = focus.dbmodel.get_identifier_value('doi')
        if doi:
            doi_iri = DOI[doi]
            yield (OWL.sameAs, doi_iri)
            yield (DCT.identifier, str(doi_iri))


@gather.er(DCT.type)
def gather_flexible_types(focus):
    # TODO: crosswalk from osf:category to something more intentional
    category = getattr(focus.dbmodel, 'category', None)
    if category:
        yield (DCT.type, OSF[category])
    if hasattr(focus, 'guid_metadata_record'):
        yield (DCT.type, focus.guid_metadata_record.resource_type_general)


@gather.er(DCT.created)
def gather_created(focus):
    if focus.rdftype == OSF.Registration:
        yield (DCT.created, getattr(focus.dbmodel, 'registered_date', None))
    else:
        yield (DCT.created, getattr(focus.dbmodel, 'created', None))


@gather.er(DCT.available)
def gather_available(focus):
    embargo = getattr(focus.dbmodel, 'embargo', None)
    if embargo:
        yield (DCT.available, embargo.end_date)


@gather.er(DCT.modified)
def gather_modified(focus):
    last_logged = getattr(focus.dbmodel, 'last_logged', None)
    if last_logged is not None:
        yield (DCT.modified, last_logged)
    else:
        yield (DCT.modified, getattr(focus.dbmodel, 'modified', None))


@gather.er(DCT.dateSubmitted, DCT.dateAccepted)
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
        yield (DCT.dateSubmitted, action_dates.get('date_submitted'))
        yield (DCT.dateAccepted, action_dates.get('date_accepted'))
        # TODO: withdrawn?


@gather.er(DCT.dateCopyrighted, DCT.rightsHolder, DCT.rights)
def gather_licensing(focus):
    license_record = getattr(focus.dbmodel, 'node_license', None)
    if license_record is not None:
        yield (DCT.dateCopyrighted, license_record.year)
        for copyright_holder in license_record.copyright_holders:
            yield (DCT.rightsHolder, copyright_holder)
        license = license_record.node_license  # yes, it is node.node_license.node_license
        if license is not None:
            if license.url:
                license_iri = rdflib.URIRef(license.url)
                yield (DCT.rights, license_iri)
                yield (license_iri, FOAF.name, license.name)
            elif license.name:
                yield (DCT.rights, license.name)


@gather.er(DCT.title)
def gather_title(focus):
    yield (DCT.title, getattr(focus.dbmodel, 'title', None))
    if hasattr(focus, 'guid_metadata_record'):
        yield (DCT.title, focus.guid_metadata_record.title)


@gather.er(DCT.language)
def gather_language(focus):
    if hasattr(focus, 'guid_metadata_record'):
        yield (DCT.language, focus.guid_metadata_record.language)


@gather.er(DCT.description)
def gather_description(focus):
    yield (DCT.description, getattr(focus.dbmodel, 'description', None))
    if hasattr(focus, 'guid_metadata_record'):
        yield (DCT.description, focus.guid_metadata_record.description)


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


@gather.er(DCT.subject)
def gather_subjects(focus):
    if hasattr(focus.dbmodel, 'subjects'):
        for subject in focus.dbmodel.subjects.all().select_related('bepress_subject'):
            # TODO: subject iri, not just text
            yield (DCT.subject, subject.text)
            if subject.bepress_subject:
                yield (DCT.subject, subject.bepress_subject.text)


@gather.er(focustype_iris=[OSF.File])
def gather_file_basics(focus):
    if isinstance(focus.dbmodel, osfdb.BaseFileNode):
        yield (OSF.file_name, getattr(focus.dbmodel, 'name', None))
        yield (OSF.file_path, getattr(focus.dbmodel, 'materialized_path', None))


@gather.er(
    DCT.hasVersion,
    focustype_iris=[OSF.File],
)
def gather_versions(focus):
    if hasattr(focus.dbmodel, 'versions'):  # quacks like BaseFileNode
        fileversions = focus.dbmodel.versions.all()[:10]  # TODO: how many?
        if fileversions.exists():  # quacks like OsfStorageFileNode
            from api.base.utils import absolute_reverse as apiv2_absolute_reverse
            for fileversion in fileversions:  # expecting version to quack like FileVersion
                fileversion_iri = rdflib.URIRef(
                    apiv2_absolute_reverse(
                        'files:version-detail',
                        kwargs={
                            'version': 'v2',  # api version
                            'file_id': focus.dbmodel._id,
                            'version_id': fileversion.identifier,
                        },
                    ),
                )
                yield (DCT.hasVersion, fileversion_iri)
                yield from _gather_fileversion(fileversion, fileversion_iri)
        else:  # quacks like non-osfstorage BaseFileNode
            checksums = getattr(focus.dbmodel, '_hashes', {})
            if checksums:
                blankversion = rdflib.BNode()
                yield (DCT.hasVersion, blankversion)
                for checksum_algorithm, checksum_value in checksums.items():
                    if ' ' not in checksum_algorithm:
                        yield (blankversion, DCT.requires, checksum_iri(checksum_algorithm, checksum_value))


def _gather_fileversion(fileversion, fileversion_iri):
    yield (fileversion_iri, RDF.type, OSF.FileVersion)
    yield (fileversion_iri, DCT.creator, OsfFocus(fileversion.creator))
    yield (fileversion_iri, DCT.created, fileversion.created)
    yield (fileversion_iri, DCT.modified, fileversion.modified)
    yield (fileversion_iri, DCT['format'], fileversion.content_type)
    yield (fileversion_iri, DCT.extent, format_dct_extent(fileversion.size))
    yield (fileversion_iri, OSF.version_number, fileversion.identifier)
    version_sha256 = (fileversion.metadata or {}).get('sha256')
    if version_sha256:
        yield (fileversion_iri, DCT.requires, checksum_iri('sha-256', version_sha256))


@gather.er(DCT.hasPart, OSF.has_file)
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
        yield (DCT.hasPart, file_focus)
        yield (OSF.has_file, file_focus)
        if (primary_file_id is not None) and file.id == primary_file_id:
            yield (DCT.requires, file_focus)


@gather.er(DCT.hasPart, DCT.isPartOf, OSF.has_child, OSF.has_parent)
def gather_parts(focus):
    if isinstance(focus.dbmodel, osfdb.AbstractNode):
        if not is_root(focus.dbmodel):
            root_focus = OsfFocus(focus.dbmodel.root)
            yield (DCT.isPartOf, root_focus)
            yield (OSF.has_root, root_focus)
        for child in osfdb.AbstractNode.objects.get_children(focus.dbmodel):
            childfocus = OsfFocus(child)
            yield (DCT.hasPart, childfocus)
            if child.parent_node == focus.dbmodel:
                yield (OSF.has_child, childfocus)
            else:
                yield (OSF.has_descendent, childfocus)
    parent = getattr(focus.dbmodel, 'parent_node', None)
    if parent is not None:
        yield (DCT.isPartOf, OsfFocus(parent))
        yield (OSF.has_parent, OsfFocus(parent))
    container = getattr(focus.dbmodel, 'target', None)
    if container is not None:
        yield (DCT.isPartOf, OsfFocus(container))


@gather.er(DCT.relation)
def gather_related_items(focus):
    related_article_doi = getattr(focus.dbmodel, 'article_doi', None)
    if related_article_doi:
        yield (DCT.relation, DOI[related_article_doi])
        yield (OSF.is_supplement_to_article, DOI[related_article_doi])
    if isinstance(focus.dbmodel, osfdb.Registration):
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
                yield (DCT.relation, artifact_iri)
                artifact_bnode = rdflib.BNode()
                yield (OSF_ARTIFACT_PREDICATES[outcome_artifact.artifact_type], artifact_bnode)
                yield (artifact_bnode, DCT.identifier, str(artifact_iri))
                yield (artifact_bnode, DCT.title, outcome_artifact.title)
                yield (artifact_bnode, DCT.description, outcome_artifact.description)


@gather.er(
    DCT.creator,
    DCT.contributor,
    focustype_iris=[OSF.Project, OSF.Component, OSF.Registration, OSF.RegistrationComponent, OSF.Preprint],
)
def gather_agents(focus):
    if focus.rdftype in (OSF.Project, OSF.Component, OSF.Registration, OSF.RegistrationComponent):
        contributor_filter_name = 'contributor__node'
    elif focus.rdftype == OSF.Preprint:
        contributor_filter_name = 'contributor__preprint'
    else:
        return
    creators = focus.dbmodel.contributors.filter(
        contributor__visible=True,
        **{contributor_filter_name: focus.dbmodel},
    )
    for user in creators:
        yield (DCT.creator, OsfFocus(user))
    contributors = focus.dbmodel.contributors.filter(
        contributor__visible=False,
        **{contributor_filter_name: focus.dbmodel},
    )
    # TODO: some nuance in contributor roles
    for user in contributors:
        yield (DCT.contributor, OsfFocus(user))


@gather.er(OSF.affiliated_institution)
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
        yield (OSF.affiliated_institution, institution_iri)
        yield (institution_iri, FOAF.name, osf_institution.name)
        yield (institution_iri, DCT.identifier, osf_institution.ror_uri)
        yield (institution_iri, DCT.identifier, osf_institution.identifier_domain)


@gather.er(OSF.funder)
def gather_funding(focus):
    if hasattr(focus, 'guid_metadata_record'):
        for funding in focus.guid_metadata_record.funding_info:
            funder_bnode = rdflib.BNode()
            yield (OSF.funder, funder_bnode)
            yield (funder_bnode, RDF.type, OSF.Funder)
            yield (funder_bnode, FOAF.name, funding.get('funder_name'))
            yield (funder_bnode, DCT.identifier, funding.get('funder_identifier'))
            yield (funder_bnode, OSF.funder_identifier_type, funding.get('funder_identifier_type'))
            yield (funder_bnode, OSF.award_number, funding.get('award_number'))
            yield (funder_bnode, OSF.award_uri, funding.get('award_uri'))
            yield (funder_bnode, OSF.award_title, funding.get('award_title'))


@gather.er(focustype_iris=[OSF.OSFUser])
def gather_user_basics(focus):
    yield (RDF.type, DCT.Agent)
    yield (FOAF.name, focus.dbmodel.fullname)
    for social_link in focus.dbmodel.social_links.values():
        if isinstance(social_link, str):
            yield (DCT.identifier, social_link)
        elif isinstance(social_link, list):
            for link in social_link:
                yield (DCT.identifier, link)
    orcid = focus.dbmodel.get_verified_external_id('ORCID', verified_only=True)
    if orcid:
        orcid_iri = ORCID[orcid]
        yield (OWL.sameAs, orcid_iri)
        yield (DCT.identifier, str(orcid_iri))
