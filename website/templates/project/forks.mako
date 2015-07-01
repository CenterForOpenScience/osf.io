<%inherit file="project/project_base.mako"/>
<%def name="title()">${node['title']} Forks</%def>

<div class="page-header visible-xs">
    <h2 class="text-300">Forks</h2>
</div>

<div class="row">
    % if node['fork_count']:
        <div class="col-md-8 col-md-offset-2 p-lg">
            <div mod-meta='{
                "tpl": "util/render_nodes.mako",
                "uri": "${node["api_url"]}get_forks/",
                "replace": true,
                "kwargs": {"sortable": false, "pluralized_node_type": "forks"}
            }'></div>
        </div>
    % else:
        <div class="col-md-8 p-lg">
                <p>There have been no forks of this project.. Forking a project means you have created a copy of it into your dashboard, and can change that copy for your own purposes. You will be the only contributor to the forked project until you add others.</p>
        </div>
        <div class="col-md-4 p-lg">
                <div class="p-lg">
                    <a href="/getting-started/#forks" class="btn btn-info"> Learn more about Forks</a>
                </div>
                <div class="p-lg">
                    % if user_name and (user['is_contributor'] or node['is_public']) and not disk_saving_mode:
                        <a class="btn btn-success" type="button" onclick="NodeActions.forkNode();">New Fork</a>
                    % endif
                </div>
        </div>
    % endif
</div>
