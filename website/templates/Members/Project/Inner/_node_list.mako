<%namespace file="_print_logs.mako" import="print_logs"/>
<script src="http://code.jquery.com/ui/1.10.3/jquery-ui.js"></script>
<%def name="node_list(nodes, default=0)">

<ul class="list-group sortable" style="margin-left: 0px;">
%for node in nodes:
    % if node.id is None or node.is_deleted:
        <% continue %>
    % endif
    <li id="projects-widget" node_id="${node.id}" class="project list-group-item" style="display: list-item;">
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
%endfor
</ul>

<script>
    $(function(){
        $('.sortable').sortable({
            containment: "parent",
            tolerance: "pointer",
            stop: function(event, ui){
                var sort_list_elm = this;
                var id_list = $(sort_list_elm).sortable("toArray", {
                   attribute: "node_id"
                });
                if(!checkListChange(id_list)){
                    $(sort_list_elm).sortable("cancel");
                }
            }
        });
    });
</script>
</%def>