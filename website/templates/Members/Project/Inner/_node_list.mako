<%namespace file="_print_logs.mako" import="print_logs"/>
<%def name="node_list(nodes, default=0)">
%for node in nodes:
	%if not node.is_deleted:
	<li id="projects-widget" class="project" style="display: list-item;">
		<h3 style="line-height:18px;">
			<span style="display:inline-block; width: 400px">
			%if not node.node_parent:
			    <a href="${node.url()}">${node.title}</a>
			%else:
				<a href="${node.url()}">${node.title}</a>
			%endif
			% if node.is_registration:
				| registered: ${node.registered_date.strftime('%Y/%m/%d %I:%M %p')}
			% endif
			</span>
			<i style="float:right;" id="icon-${node.id}" class="icon-plus" onclick="openCloseNode('${node.id}');"></i>
		</h3>
		
		<div class="body hide" id="body-${node.id}" style="overflow:hidden;">
		      Recent Activity
		      %if node.logs:
		      	${print_logs(reversed(node.logs.objects()), n=3)}
		      %endif
		</div>
	</li>
	%endif
%endfor
</%def>