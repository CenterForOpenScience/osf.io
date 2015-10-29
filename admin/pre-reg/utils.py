from framework.utils import iso8601format
from website.project.metadata.utils import serialize_meta_schema
from website.project.model import Node


def serialize_draft_registration_approval(approval, auth=None):
    """Build a JSON object of a DraftRegistrationApproval object
    :param approval: DraftRegistrationApproval object
    :return: Serialized DraftRegistrationApproval object
    """
    return {
        '_id': approval._id,
        'end_date': iso8601format(approval.end_date),
        '_version': approval._version,
        # list of user ids for authorizers with tokens
        'approval_state': approval.approval_state.keys(),
        'state': approval.state,
        'initiation_date': iso8601format(approval.initiation_date)
    }


def serialize_draft_registration(draft, auth=None):
    """Build a JSON object of a DraftRegistration object without urls
    :param draft: DraftRegistration object
    :return: Serialized DraftRegistration object
    """
    from website.profile.utils import serialize_user  # noqa

    # node = draft.branched_from

    return {
        'pk': draft._id,
        'branched_from': serialize_node(draft.branched_from, auth),
        'initiator': serialize_user(draft.initiator, full=True),
        'registration_metadata': draft.registration_metadata,
        'registration_schema': serialize_meta_schema(draft.registration_schema),
        'initiated': str(draft.datetime_initiated),
        'updated': str(draft.datetime_updated),
        'flags': draft.flags,
        'requires_approval': draft.requires_approval,
        # 'is_pending_approval': draft.is_pending_review,
        # 'is_approved': draft.is_approved,
        'approval': serialize_draft_registration_approval(draft.approval)
    }


def serialize_node(node, primary=False):
    """Build a JSON object of a node
    :param node: Node object
    :param auth: Auth oject of current user
    :return: Serialized node object
    """

    parent = node.parent_node

    data = {
        'node': {
            'id': node._primary_key,
            'title': node.title,
            'category': node.category_display,
            'category_short': node.category,
            'node_type': node.project_or_component,
            'description': node.description or '',
            'url': node.url,
            'api_url': node.api_url,
            'absolute_url': node.absolute_url,
            'display_absolute_url': node.display_absolute_url,
            'is_public': node.is_public,
            'is_archiving': node.archiving,
            'date_created': iso8601format(node.date_created),
            'date_modified': iso8601format(node.logs[-1].date) if node.logs else '',
            'tags': [tag._primary_key for tag in node.tags],
            'children': bool(node.nodes),
            'is_registration': node.is_registration,
            'is_retracted': node.is_retracted,
            'pending_retraction': node.pending_retraction,
            'retracted_justification': getattr(node.retraction, 'justification', None),
            'embargo_end_date': node.embargo_end_date.strftime("%A, %b. %d, %Y") if node.embargo_end_date else False,
            'pending_embargo': node.pending_embargo,
            'registered_from_url': node.registered_from.url if node.is_registration else '',
            'registered_date': iso8601format(node.registered_date) if node.is_registration else '',
            'root_id': node.root._id,
            'registered_meta': node.registered_meta,
            'registered_schema': serialize_meta_schema(node.registered_schema),
            'registration_count': len(node.node__registrations),
            'is_fork': node.is_fork,
            'forked_from_id': node.forked_from._primary_key if node.is_fork else '',
            'forked_from_display_absolute_url': node.forked_from.display_absolute_url if node.is_fork else '',
            'forked_date': iso8601format(node.forked_date) if node.is_fork else '',
            'fork_count': len(node.forks),
            'templated_count': len(node.templated_list),
            'watched_count': len(node.watchconfig__watched),
            'private_links': [x.to_json() for x in node.private_links_active],
            'points': len(node.get_points(deleted=False, folders=False)),
            'piwik_site_id': node.piwik_site_id,
            'comment_level': node.comment_level,
            'has_comments': bool(getattr(node, 'commented', [])),
            'has_children': bool(getattr(node, 'commented', False)),
            'identifiers': {
                'doi': node.get_identifier_value('doi'),
                'ark': node.get_identifier_value('ark'),
            },
        },
        'parent_node': {
            'exists': parent is not None,
            'id': parent._primary_key if parent else '',
            'title': parent.title if parent else '',
            'category': parent.category_display if parent else '',
            'url': parent.url if parent else '',
            'api_url': parent.api_url if parent else '',
            'absolute_url': parent.absolute_url if parent else '',
            'registrations_url': parent.web_url_for('node_registrations') if parent else '',
            'is_public': parent.is_public if parent else '',
        },
        # TODO: Namespace with nested dicts
        'addons_enabled': node.get_addon_names(),
        'node_categories': Node.CATEGORY_MAP,
    }
    return data
