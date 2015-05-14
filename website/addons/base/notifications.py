# -*- coding: utf-8 -*-

from furl import furl
from datetime import datetime

from website.notifications.emails import notify


def file_notify(user, node, event, metadata, provider):
    f_url = furl(node.absolute_url)
    path = metadata['path']
    timestamp = datetime.utcnow()
    if event == 'delete':
        message = 'deleted <strong>"{}"</strong>.'.format(path)  # only has path
        f_url.path = node.web_url_for('collect_file_trees')
    else:
        try:
            name = metadata['name']
        except KeyError:
            name = path
        f_url.path = node.web_url_for('addon_view_or_download_file', path=path, provider=provider)
        if event == 'create':
            message = 'uploaded file <strong>"{}"</strong>.'.format(name)
        elif event == 'update':
            message = 'updated file <strong>"{}"</strong>.'.format(name)
        elif event == 'create_folder':
            message = 'added folder <strong>"{}"</strong>.'.format(name)

    notify(
        uid=node._id,
        event=path + '_file_updated',
        user=user,
        node=node,
        timestamp=timestamp,
        message=message,
        gravatar_url=user.gravatar_url,
        url=f_url.url
    )
