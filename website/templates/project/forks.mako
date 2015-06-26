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
	       <div class="alert alert-info m-xl text-center">There have been no forks of this project.</div>
            <div class="text-center">
                <p>Forking a project means you have created a copy of it into your dashboard, and can change that copy for your own purposes. You will be the only contributor to the forked project until you add others.</p>
                <a href="/getting-started/#forks" class="btn btn-info"> Learn more about Forks</a>
            </div>
            </div>
	    % endif
    </div>
</div>
