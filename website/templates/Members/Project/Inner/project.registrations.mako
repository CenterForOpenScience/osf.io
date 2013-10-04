<%inherit file="project.view.mako" />
<%namespace file="_node_list.mako" import="node_list"/>

<%
    is_contributor = node_to_use.is_contributor(user)
    editable = is_contributor and not node_to_use.is_registration
%>

<div class="page-header"><div style="float:right;">
    % if editable and node_to_use.category == 'project':
        <a href="${node_to_use.url()}/register" class="btn" type="button">New Registration</a>
    % else:
        <a class="btn disabled" type="button">New Registration</a>
    % endif
    </div>
	<h1>Registrations</h1>
</div>
% if node_to_use.registration_list:
	${node_list([node_to_use.load(nid) for nid in node_to_use.registration_list], profile_id=user._id if user else None, profile_fullname=user.fullname if user else None)}
% else:
    There have been no registrations of this specific project. For a list of the most viewed and most recent public registrations on the Open Science Framework, click <a href="/explore/activity/">here</a>.
% endif