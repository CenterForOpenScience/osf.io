from mako.template import Template

from framework import request
from framework.auth import get_current_user

from website.project.decorators import must_be_contributor_or_public
from website.project.decorators import must_have_addon

from ..api import Figshare

@must_be_contributor_or_public
@must_have_addon('github', 'node')
def figshare_hgrid_data_contents(*args, **kwargs):
    pass

def figshare_dummy_folder(node_settings, auth, parent=None, **kwargs):
    if not node_settings.figshare_id:
       return

    connect = Figshare.from_settings(node_settings.user_settings)

    rv = {
        'addonName': 'FigShare',
        'maxFilesize': node_settings.config.max_file_size,
        'uid': 'figshare:{0}'.format(node_settings._id),
        'name': 'FigShare: {0}/{1}'.format(
            node_settings.user, node_settings.repo,
        ),
        'parent_uid': parent or 'null',
        'type': 'folder',
        'can_view': False,
        'can_edit': False,
        'permission': False,
    }

    return rv

