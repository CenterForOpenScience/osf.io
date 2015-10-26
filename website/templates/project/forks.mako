<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Forks</%def>

<div class="page-header visible-xs">
    <h2 class="text-300">Forks</h2>
</div>

<div class="row">
        <div class="col-xs-9 col-sm-8">

    % if node['fork_count']:
            <div mod-meta='{
                "tpl": "util/render_nodes.mako",
                "uri": "${node["api_url"]}get_forks/",
                "replace": true,
                "kwargs": {"sortable": false, "pluralized_node_type": "forks"}
            }'></div>
    % else:
            <p class="m-md">This project has no forks. A fork is a copy of a project that you can change without
            affecting the original project.</p>
    % endif
    </div>
        <div class="col-xs-3 col-sm-4">
                <div class="m-md">
                    % if user_name and (user['is_contributor'] or node['is_public']) and not disk_saving_mode:
                        <a class="btn btn-success" type="button" onclick="NodeActions.forkNode();">New fork</a>
                    % endif
                </div>
        </div>
</div>
