<%inherit file="base.mako"/>
<%def name="title()">Forks</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>

% if node_fork_count:
    <div mod-meta='{
            "tpl": "util/render_nodes.mako",
            "uri": "${node_api_url}get_forks/",
            "replace": true
        }'></div>
% else:
    There have been no forks.
% endif
</%def>
