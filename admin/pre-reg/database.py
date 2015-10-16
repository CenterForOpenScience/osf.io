import httplib as http

from modularodm import Q

from website.project.model import MetaSchema, DraftRegistration, DraftRegistrationApproval
from framework.mongo.utils import get_or_http_error
from framework.auth.core import User
from framework.auth import Auth
from website.project.metadata.utils import serialize_meta_schema
from website.app import do_set_backends, init_addons
from website import settings as osf_settings

import utils

init_addons(osf_settings, routes=False)
do_set_backends(osf_settings)

# TODO[lauren]: change once users have osf id associated with them
adminUser = User.load('dsmpw')


def get_all_drafts():
    """Retrieves all submitted prereg drafts from OSF db
    :return: Dict of submitted prereg drafts
    """
    # TODO[lauren]: add query parameters to only retrieve submitted drafts
    # they will have an approval associated with them
    all_drafts = DraftRegistration.find()
    # TODO[lauren]: change to current user
    auth = Auth(adminUser)

    serialized_drafts = {
        'drafts': [utils.serialize_draft_registration(d, auth) for d in all_drafts]
    }
    return serialized_drafts

get_schema_or_fail = lambda query: get_or_http_error(MetaSchema, query)


def get_draft(draft_pk):
    """Retrieves a specified draft from the OSF db
    :param draft_pk: Unique id for draft
    :return: Serialized draft obj
    """
    # TODO[lauren]: change to current user
    auth = Auth(adminUser)

    draft = DraftRegistration.find(
        Q('_id', 'eq', draft_pk)
    )

    return utils.serialize_draft_registration(draft[0], auth), http.OK


def get_draft_obj(draft_pk):
    """Retrieves a specified draft from the OSF db
    :param draft_pk: Unique id for draft
    :return: Draft obj
    """
    # TODO[lauren]: change to current user
    auth = Auth(adminUser)

    draft = DraftRegistration.find(
        Q('_id', 'eq', draft_pk)
    )

    return draft[0], auth


def get_approval_obj(approval_pk):
    """Retrieves a specified approval from the OSF db
    :param approval_pk: Unique id for approval
    :return: Approval obj
    """
    # TODO[lauren]: change to current user
    auth = Auth(adminUser)

    approval = DraftRegistrationApproval.find(
        Q('_id', 'eq', approval_pk)
    )

    return approval[0], auth


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
