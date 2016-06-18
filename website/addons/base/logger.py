import abc

class AddonNodeLogger(object):
    """Helper class for adding correctly-formatted addon logs to nodes.

    :param Node node: The node to add logs to
    :param Auth auth: Authorization of the person who did the action.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def addon_short_name(self):
        pass

    def _log_params(self):
        node_settings = self.node.get_addon(self.addon_short_name, deleted=True)
        return {
            'project': self.node.parent_id,
            'node': self.node._primary_key,
            'folder_id': node_settings.folder_id,
            'folder_name': node_settings.folder_name,
            'folder': node_settings.folder_path
        }

    def __init__(self, node, auth, path=None):
        self.node = node
        self.auth = auth
        self.path = path

    def log(self, action, extra=None, save=False):
        """Log an event. Wraps the Node#add_log method, automatically adding
        relevant parameters and prefixing log events with addon_short_name.

        :param str action: Log action. Should be a class constant from NodeLog.
        :param dict extra: Extra parameters to add to the ``params`` dict of the
        new NodeLog.
        """
        params = self._log_params()
        # If logging a file-related action, add the file's view and download URLs
        if self.path:
            params.update({
                'urls': {
                    'view': self.node.web_url_for('addon_view_or_download_file', path=self.path, provider=self.addon_short_name),
                    'download': self.node.web_url_for(
                        'addon_view_or_download_file',
                        path=self.path,
                        provider=self.addon_short_name
                    )
                },
                'path': self.path,
            })
        if extra:
            params.update(extra)

        self.node.add_log(
            action='{0}_{1}'.format(self.addon_short_name, action),
            params=params,
            auth=self.auth
        )
        if save:
            self.node.save()
