<%inherit file="base.mako"/>
<%def name="title()">Registrations</%def>
<%def name="content()">
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>
<div class="page-header">
    <div class="pull-right">
    % if user_can_edit and node_category == 'project':
        <a href="${node_url}register" class="btn btn-default" type="button">New Registration</a>
    % else:
        <a class="btn btn-default disabled" type="button">New Registration</a>
    % endif
    </div>
	<h1>Registrations</h1>
</div>

% if node_registration_count:
    <div mod-meta='{
            "tpl": "util/render_nodes.mako",
            "uri": "${node_api_url}get_registrations/",
            "replace": true
        }'></div>
% else:
	There have been no registrations of this specific project.
    For a list of the most viewed and most recent public registrations on the
    Open Science Framework, click <a href="/explore/activity/">here</a>.
% endif
</%def>
