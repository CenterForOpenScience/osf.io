
import httplib as http

from modularodm import Q

from website.project.model import MetaSchema, DraftRegistration, DraftRegistrationApproval
from framework.mongo.utils import get_or_http_error
from website.project.metadata.utils import serialize_meta_schema

import utils

# TODO[lauren]: check which serializers used auth

def get_all_drafts():
    """Retrieves all submitted prereg drafts from OSF db
    :return: Dict of submitted prereg drafts
    """
    # TODO[lauren]: add query parameters to only retrieve submitted drafts
    # they will have an approval associated with them
    prereg_schema = MetaSchema.find_one(
        Q('name', 'eq', 'Prereg Challenge') &
        Q('schema_version', 'eq', 2)
    )
    all_drafts = DraftRegistration.find(
        Q('registration_schema', 'eq', prereg_schema) &
        Q('approval', 'ne', None)
    )

    # import ipdb; ipdb.set_trace()

    serialized_drafts = {
        'drafts': [utils.serialize_draft_registration(d) for d in all_drafts]
    }
    return serialized_drafts

get_schema_or_fail = lambda query: get_or_http_error(MetaSchema, query)


def get_draft(draft_pk):
    """Retrieves a specified draft from the OSF db
    :param draft_pk: Unique id for draft
    :return: Serialized draft obj
    """
    draft = DraftRegistration.find(
        Q('_id', 'eq', draft_pk)
    )

    return utils.serialize_draft_registration(draft[0]), http.OK


def get_draft_obj(draft_pk):
    """Retrieves a specified draft from the OSF db
    :param draft_pk: Unique id for draft
    :return: Draft obj
    """
    draft = DraftRegistration.find(
        Q('_id', 'eq', draft_pk)
    )

    return draft[0]


def get_approval_obj(approval_pk):
    """Retrieves a specified approval from the OSF db
    :param approval_pk: Unique id for approval
    :return: Approval obj
    """
    approval = DraftRegistrationApproval.find(
        Q('_id', 'eq', approval_pk)
    )

    return approval[0]


def get_metaschemas():
    """Retrieves all MetaSchemas from the OSF db
    :return: Dict of serialized MetaSchemas
    """
    all_schemas = MetaSchema.find()
    serialized_schemas = {
        'schemas': [utils.serialize_meta_schema(s) for s in all_schemas]
    }
    return serialized_schemas


def get_metaschema(schema_name, schema_version=1):
    """Retrieves a specified MetaSchemas from the OSF db
    :param schema_name: name of schema to retrieve
    :param schema_version: version of schema to retrieve
    :return: Serialized MetaSchema
    """
    meta_schema = get_schema_or_fail(
        Q('name', 'eq', schema_name) &
        Q('schema_version', 'eq', schema_version)
    )
    return serialize_meta_schema(meta_schema), http.OK
