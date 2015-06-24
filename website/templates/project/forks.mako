<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Forks</%def>

<div class="page-header visible-xs">
    <h2 class="text-300">Forks</h2>
</div>

<div class="row">
	<div class="col-md-8 col-md-offset-2">

    % if node['fork_count']:
        <div mod-meta='{
            "tpl": "util/render_nodes.mako",
            "uri": "${node["api_url"]}get_forks/",
            "replace": true,
            "kwargs": {"sortable": false, "pluralized_node_type": "registrations"}
        }'></div>
    % else:
        <div>There have been no forks of this project.</div>
    % endif


    </div>
</div>
