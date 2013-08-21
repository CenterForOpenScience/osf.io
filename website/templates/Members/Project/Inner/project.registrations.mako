<%inherit file="project.view.mako" />
<%namespace file="_node_list.mako" import="node_list"/>

<div class="page-header">
    <div style="float:right;"><a href="${node_to_use.url()}/register" class="btn" type="button">New Registration</a></div>
	<h1>Registrations</h1>
</div>
% if node_to_use.node_registrations:
	${node_list(node_to_use.node_registrations)}
%else:
	There have been no registrations of this specific project. For a list of the most viewed and most recent public registrations on the Open Science Framework, click <a href="/explore/activity/">here</a>.
%endif