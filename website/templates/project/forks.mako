<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Forks</%def>

<div class="page-header">
    <h2>Forks</h2>
</div>

% if node['fork_count']:
    <div mod-meta='{
            "tpl": "util/render_nodes.mako",
            "uri": "${node["api_url"]}get_forks/",
            "replace": true
        }'></div>
% else:
    <div>There have been no forks of this project.</div>
% endif
