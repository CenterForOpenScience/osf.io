<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>
<div mod-meta='{"tpl": "project/base.mako", "replace": true}'></div>

<div class="page-header"><div style="float:right;">
    % if user_can_edit and node_category == 'project':
        <a href="${node_url}register" class="btn" type="button">New Registration</a>
    % else:
        <a class="btn disabled" type="button">New Registration</a>
    % endif
    </div>
	<h1>Registrations</h1>
</div>
% if node_registrations:
    % for registration in node_registrations:
        <div mod-meta='{
                "tpl": "util/render_node.mako",
                "uri": "${registration['registration_api_url']}get_summary/",
                "replace": true
            }'></div>
    % endfor
% else:
    There have been no registrations of this specific project. For a list of the most viewed and most recent public registrations on the Open Science Framework, click <a href="/explore/activity/">here</a>.
% endif

<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>