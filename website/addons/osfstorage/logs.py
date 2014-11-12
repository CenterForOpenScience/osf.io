#!/usr/bin/env python
# encoding: utf-8


def build_log_urls(node, path):
    return {
        'view': node.web_url_for(
            'osf_storage_view_file',
            path=path,
        ),
        'download': node.web_url_for(
            'osf_storage_view_file',
            path=path,
            action='download',
        ),
    }


class OsfStorageNodeLogger(object):

    def __init__(self, node, auth, path=None):
        self.node = node
        self.auth = auth
        self.path = path

    def log(self, action, extra=None, save=False):
        """Log an event. Wraps the Node#add_log method, automatically adding
        relevant parameters and prefixing log events with `"osf_storage_"`.

        :param str action: Log action. Should be a class constant from NodeLog.
        :param dict extra: Extra parameters to add to the ``params`` dict of the
            new NodeLog.
        """
        params = {
            'project': self.node.parent_id,
            'node': self.node._primary_key,
        }
        # If logging a file-related action, add the file's view and download URLs
        if self.path:
            params.update({
                'urls': build_log_urls(self.node, self.path),
                'path': self.path,
            })
        if extra:
            params.update(extra)
        # Prefix the action with osf_storage_
        self.node.add_log(
            action='osf_storage_{0}'.format(action),
            params=params,
            auth=self.auth,
        )
        if save:
            self.node.save()
