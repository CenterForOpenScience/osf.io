from __future__ import unicode_literals

import logging

from framework.auth.core import Auth
from django.utils import timezone

from osf.models.node import AbstractNode, Node, NodeLog
from osf.exceptions import NodeStateError


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

    def convert_draft_node_to_node(self, auth):
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

    def register_node(self, schema, auth, draft_registration, parent=None, child_ids=None, provider=None):
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
        self.copy_editable_fields(draft_registration, auth=auth, save=True)
        # Queued downstream by mails.send_mail
        self.subscribe_contributors_to_node()

        # Calls super on Node, since self is no longer a DraftNode
        return super(Node, self).register_node(schema, auth, draft_registration, parent, child_ids, provider)
