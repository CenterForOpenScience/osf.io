<%inherit file="membersOuter.mako" />
<%namespace file="_node_list.mako" import="node_list"/>
<div class="row">
     <div class="span6">
        <div class="page-header">
         <div style="float:right;"><a class="btn" href="/project/new">New Project</a></div>
         <h3 style="margin-bottom:10px;">Projects</h3>
        </div>
         % if user.node_contributed:
             ${node_list(reversed([p for p in user.node_contributed.objects() if p.category=='project']), default="user_dashboard")}
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