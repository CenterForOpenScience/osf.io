<%inherit file="project.view.mako" />
<%namespace file="_node_list.mako" import="node_list"/>

##% if node_to_use.node__forked:
##	${node_list(node_to_use.node__forked)}
% if node_to_use.fork_list:
    ${node_list([node_to_use.load(nid) for nid in node_to_use.fork_list], profile_id=user._id if user else None)}
% else:
	There have been no forks.
% endif