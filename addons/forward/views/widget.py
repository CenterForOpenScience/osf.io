from website.project.decorators import (
    must_be_valid_project, must_have_addon, must_be_contributor_or_public
)

from addons.forward.utils import serialize_settings, settings_complete


@must_be_valid_project
@must_have_addon('forward', 'node')
@must_be_contributor_or_public
def forward_widget(node_addon, **kwargs):

    out = serialize_settings(node_addon)
    out['complete'] = settings_complete(node_addon)
    out.update(node_addon.config.to_json())
    return out
