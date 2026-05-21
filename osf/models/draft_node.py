import logging

from framework.auth.core import Auth
from django.utils import timezone

from .node import AbstractNode, Node, NodeLog
from osf import features
from osf.exceptions import NodeStateError
from osf.utils.requests import get_current_request
import waffle


logger = logging.getLogger(__name__)


class DraftNode(AbstractNode):
    """
    DraftNode class: Instance of AbstractNode(TypedModel). All things that inherit
    from AbstractNode will appear in the same table and will be differentiated by the `type` column.

    DraftNodes are created as part of the registration process when a previous Node does not exist.  It is a
    holding tank primarily for file storage.  Upon finalizing the registration, the DraftNode is converted into
    a Node.

    DraftNodes are hidden. They are not accessible in search, and they are not public.
    """

    def is_draft_node_prevented_to_be_changed_node(self):
        request = get_current_request()
        if request:
            return waffle.flag_is_active(request, features.PREVENT_DRAFT_NODE_BE_CHANGED_TO_NODES)
        try:
            flag = waffle.get_waffle_flag_model().objects.get(
                name=features.PREVENT_DRAFT_NODE_BE_CHANGED_TO_NODES
            )
            return flag.everyone
        except waffle.get_waffle_flag_model().DoesNotExist:
            return False

    def set_privacy(self, permissions, *args, **kwargs):
        raise NodeStateError('You may not set privacy for a DraftNode.')

    def clone(self):
        raise NodeStateError('A DraftNode may not be forked, used as a template, or registered.')

    # Overrides AbstractNode.update_search
    def update_search(self):
        """
        In the off-chance a DraftNode gets turned public, ensure it doesn't get sent to search
        """
        return

    def can_view(self, auth):
        return self.registered_draft.first().can_view(auth)

    def can_edit(self, auth=None, user=None):
        return self.registered_draft.first().can_edit(auth, user)

    def convert_draft_node_to_node(self, auth):
        if self.is_draft_node_prevented_to_be_changed_node():
            raise NodeStateError('DraftNodes cannot be converted to Nodes.')

        self.recast('osf.node')
        self.save()

        log_params = {
            'node': self._id
        }

        log_action = NodeLog.PROJECT_CREATED_FROM_DRAFT_REG
        self.add_log(
            log_action,
            params=log_params,
            auth=Auth(user=auth.user),
            log_date=timezone.now()
        )
        return

    def register_node(self, schema, auth, draft_registration, parent=None, child_ids=None, provider=None, manual_guid=None):
        """Converts the DraftNode to a Node, copies editable fields from the DraftRegistration back to the Node,
         and then registers the Node

        :param schema: Schema object
        :param auth: All the auth information including user, API key.
        :param data: Form data
        :param parent Node: parent registration of registration to be created
        :param provider RegistrationProvider: provider to submit the registration to
        """
        self.convert_draft_node_to_node(auth)
        # Copies editable fields from the DraftRegistration back to the Node
        self.copy_editable_fields(draft_registration, save=True)

        # Calls super on Node, since self is no longer a DraftNode
        return super(Node, self).register_node(schema, auth, draft_registration, parent=parent, child_ids=child_ids, provider=provider, manual_guid=manual_guid)
