<%inherit file="membersOuter.mako" />
<%namespace file="_node_list.mako" import="node_list"/>
<%
    if user.node__contributed:
        nodes = [
            node for node in user.node__contributed
            if node.category == 'project'
            and not node.is_registration
        ]
    else:
        nodes = []
%>
<div class="row">
     <div class="span6">
        <div class="page-header">
         <div style="float:right;"><a class="btn" href="/project/new">New Project</a></div>
         <h3 style="margin-bottom:10px;">Projects</h3>
        </div>
         % if nodes:
             ${node_list(reversed(nodes), default="user_dashboard", profile_id=user._id if user else None)}
         %endif
     </div>
     <div class="row">
         <div class="span6">
            <div class="page-header">
             <h3 style="margin-bottom:10px;">Watched Projects</h3>
            </div>
         </div>
     </div>
</div>
<script>
</script>