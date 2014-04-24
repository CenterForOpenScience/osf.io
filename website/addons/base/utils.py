from framework.auth.decorators import Auth


class NodeLogger(object):
    """Helper class for adding correctly-formatted Dropbox logs to nodes.

    :param Node node: The node to add logs to
    :param Auth auth: Authorization of the person who did the action.
    :param str foreign_user: Name of non-OSF user; used for services with
        webhooks such as GitHub and Trello
    :param GuidFile file_obj: File object for file-related logs.
    :param str path: Path to file
    :param datetime date: Optional log date

    """

    NAME = ''

    # TODO: Generalize to non-file add-ons
    def __init__(self, node, auth, foreign_user=None, file_obj=None, path=None, date=None):
        self.node = node
        self.auth = auth
        self.foreign_user = foreign_user
        self.file_obj = file_obj
        self.path = path
        self.date = date

    def build_params(self):
        """Build `params` dictionary to pass to `Node::add_log`. Should be
        overridden by most subclasses.

        """
        return {
            'project': self.node.parent_id,
            'node': self.node._id,
        }

    def log(self, action, extra=None, save=False):
        """Log an event. Wraps the Node#add_log method, automatically adding
        relevant parameters and prefixing log events with `"dropbox_"`.

        :param str action: Log action. Should be a class constant from NodeLog.
        :param dict extra: Extra parameters to add to the ``params`` dict of the
            new NodeLog.
        :param bool save: Save changes to node.

        """
        params = self.build_params()
        if extra:
            params.update(extra)
        # Prefix the action with name
        self.node.add_log(
            action='{0}_{1}'.format(self.NAME, action),
            params=params,
            auth=self.auth,
            foreign_user=self.foreign_user,
            log_date=self.date,
        )
        if save:
            self.node.save()
