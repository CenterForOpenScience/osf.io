<%inherit file="base.mako"/>
<%def name="title()">Registrations</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/project_header.mako", "replace": true}'></div>
<div class="page-header">
    <div class="pull-right">
    % if user['can_edit'] and node['category'] == 'project':
        <a href="${node['url']}register" class="btn btn-default" type="button">New Registration</a>
    % else:
        <a class="btn btn-default disabled" type="button">New Registration</a>
    % endif
    </div>
	<h1>Registrations</h1>
</div>

% if node["registration_count"]:
    <div mod-meta='{
            "tpl": "util/render_nodes.mako",
            "uri": "${node["api_url"]}get_registrations/",
            "replace": true
        }'></div>
% else:
	There have been no registrations of this specific ${node['category']}.
    For a list of the most viewed and most recent public registrations on the
    Open Science Framework, click <a href="/explore/activity/">here</a>.

% endif
</%def>
