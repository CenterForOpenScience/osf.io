<%inherit file="project.view.mako" />
<%namespace file="_node_list.mako" import="node_list"/>

% if node_to_use.node__forked:
	${node_list(node_to_use.node__forked)}
%else:
	There have been no forks.
%endif