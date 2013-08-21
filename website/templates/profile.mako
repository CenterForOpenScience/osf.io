###############################################################################

<%
    from framework.analytics import get_total_activity_count


##    public_projects = [p for p in profile.node_contributed.objects() if p.category=='project' and p.is_public and not p.is_deleted] if profile.node_contributed else []
##    public_nodes = [p for p in profile.node_contributed.objects() if not p.category=='project' and p.is_public and not p.is_deleted] if profile.node_contributed else []
    visible_nodes = [
        node for node in profile.node__contributed
        if node.is_public and not node.is_deleted
    ]
    public_projects = [node for node in visible_nodes if node.category == 'project']
    public_nodes = [node for node in visible_nodes if node.category != 'project']

##    count_total_projects = len([p for p in profile.node_contributed.objects() if p.category=='project' and not p.is_deleted]) if profile.node_contributed else 0
    count_total_projects = len([p for p in profile.node__contributed if p.category=='project' and not p.is_deleted]) if profile.node__contributed else 0
    count_public_projects = len(public_projects)

    count_total_activity = get_total_activity_count(profile._primary_key)
    count_total_activity = count_total_activity if count_total_activity else 0
%>

<%inherit file="contentContainer.mako" />
<%namespace file="_node_list.mako" import="node_list"/>
<div class="page-header">
    <script>
        $(function() {
            $('#profile-fullname').editable({
               type:  'text',
               pk:    '${profile._primary_key}',
               name:  'fullname',
               url:   '/profile/${profile._primary_key}/edit',
               title: 'Edit Full Name',
               placement: 'bottom',
               value: '${profile.fullname}',
               success: function(data){
                    document.location.reload(true);
               }
            });
        });
    </script>
    <img src="${filters.gravatar(profile, size=settings.gravatar_size_profile)}" />
    <h1 id="${'profile-dfullname' if user and user._primary_key==profile._primary_key else ''}" style="display:inline-block">${profile.fullname}</h1>
    %if not profile.username:
   <p>This profile is currently unclaimed; others have added this person as a contributor by inputting their name and email. If you'd like to claim this profile, click here, and we'll send the address on file an email with a verification link. Once verified, you'll be able to connect a registered account to this name.</p>
   %endif
</div>

<div class="row">
    <div class="span4">
        <table class="table plain">
            <tr><td>Name</td>           <td id="${'profile-fullname' if user and user._primary_key==profile._primary_key else ''}">${profile.fullname}</td></tr>
            <tr><td>Location</td>       <td></td></tr>
            <tr><td>Member Since</td>   <td>${profile.date_registered.strftime("%Y-%m-%d")}</td></tr>
            <tr><td>Public Profile</td> <td><a href="/profile/${profile._primary_key}">/profile/${profile._primary_key}</td></tr>
        </table>
    </div>
    <div class="span4">&nbsp;
    </div>
    <div class="span4">
        <h2>
            ${count_total_activity} activity point${'s' if count_total_activity!=1 else ''}<br /> 
            ${count_total_projects} project${'s' if count_total_projects!=1 else ''}, ${count_public_projects} public
        </h2>
    </div>
</div>
<hr />
<div class="row">
    <div class="span6">
        <h3 style="margin-bottom:10px;">Public Projects </h3>
        % if len(public_projects) > 0:
            ${node_list(reversed(public_projects))}
        %else:
            <p>None at this time</p>
        %endif
    </div>
    <div class="span6">
        <h3 style="margin-bottom:10px;">Public Nodes </h3>
        % if len(public_nodes) > 0:
            ${node_list(reversed(public_nodes))}
        %else:
            <p>None at this time</p>
        %endif
    </div>
</div>