<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

% if node_fork_count:
    <div mod-meta='{
            "tpl": "util/render_nodes.mako",
            "uri": "${node_api_url}get_forks/",
            "replace": true
        }'></div>
% else:
	There have been no forks.
% endif

<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>