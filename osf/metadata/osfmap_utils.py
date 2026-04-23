from osf.metadata.rdfutils import (
    DCTERMS,
    OSF,
    OSFIO,
    without_namespace,
)
from osf import models as osfdb


def is_osf_component(osf_node) -> bool:
    return (
        isinstance(osf_node, osfdb.AbstractNode)
        and osf_node.root_id != osf_node.id
    )


def osfmap_type_from_model(model_cls, *, is_component=None):
    if issubclass(model_cls, osfdb.OSFUser):
        return DCTERMS.Agent
    if issubclass(model_cls, osfdb.BaseFileNode):
        return OSF.File
    if issubclass(model_cls, osfdb.Preprint):
        return OSF.Preprint
    if issubclass(model_cls, osfdb.Registration):
        if is_component is None:
            raise ValueError(f'osfmap_type_from_model requires `is_component` for {model_cls}')
        return (
            OSF.RegistrationComponent
            if is_component
            else OSF.Registration
        )
    if issubclass(model_cls, osfdb.Node):
        if is_component is None:
            raise ValueError(f'osfmap_type_from_model requires `is_component` for {model_cls}')
        return (
            OSF.ProjectComponent
            if is_component
            else OSF.Project
        )
    raise LookupError(model_cls)


def osfmap_type(osf_obj):
    if isinstance(osf_obj, osfdb.Guid):
        osf_obj = osf_obj.referent
    return osfmap_type_from_model(type(osf_obj), is_component=is_osf_component(osf_obj))


def osf_iri(guid_or_model):
    """return a rdflib.URIRef or None

    @param guid_or_model: a string, Guid instance, or another osf model instance
    @returns rdflib.URIRef or None
    """
    guid = osfdb.base.coerce_guid(guid_or_model)
    return OSFIO[guid._id]


def osfid_from_iri(iri: str) -> str:
    if not iri.startswith(OSFIO):
        raise ValueError(f'expected iri starting with "{OSFIO}" (got {iri!r})')
    _osfid = without_namespace(iri, OSFIO)
    if not _osfid or '/' in _osfid:
        raise ValueError(f'expected iri path with exactly one segment (got {_osfid!r} from {iri!r})')
    return _osfid
