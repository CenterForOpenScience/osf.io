
<div mod-meta='{"tpl": "header.mako", "replace": true}'></div>

<div class="page-header">

    % if user_is_profile:
    <script>
        $(function() {
            $('#profile-fullname').editable({
                type:  'text',
                pk:    '${user_id}',
                name:  'fullname',
                url:   '/api/v1/profile/${user_id}/edit/',
                title: 'Edit Full Name',
                placement: 'bottom',
                value: '${fullname}',
                success: function(data) {
                    document.location.reload(true);
                }
            });
        });
    </script>
    % endif
    <img src="${gravatar_url}" />
    <h1 id="${'profile-fullname' if user_is_profile else ''}" style="display:inline-block">${fullname}</h1>

</div>

<div class="row">
    <div class="span4">
        <table class="table plain">
            <tr><td>Name</td>           <td id="${'profile-fullname' if user_is_profile else ''}">${fullname}</td></tr>
            <tr><td>Location</td>       <td></td></tr>
            <tr><td>Member Since</td>   <td>${date_registered}</td></tr>
            <tr><td>Public Profile</td> <td><a href="/profile/${user_id}/">/profile/${user_id}/</td></tr>
        </table>
    </div>
    <div class="span4">&nbsp;
    </div>
    <div class="span4">
        <h2>
           ${activity_points} activity point${'s' if activity_points != 1 else ''}<br />
           ##${number_projects} project${'s' if number_projects !=1  else ''}, ${number_public_projects} public
        </h2>
    </div>
</div>
<hr />
<div class="row">
    <div class="span6">
        <h3 style="margin-bottom:10px;">Public Projects</h3>

        <div mod-meta='{
                "tpl" : "util/render_nodes.mako",
                "uri" : "/api/v1/profile/${user_id}/public_projects/",
                "replace" : true,
                "kwargs" : {"sortable" : true}
            }'></div>
    </div>
    <div class="span6">
        <h3 style="margin-bottom:10px;">Public Components</h3>
        <div mod-meta='{
                "tpl" : "util/render_nodes.mako",
                "uri" : "/api/v1/profile/${user_id}/public_components/",
                "replace" : true,
                "kwargs" : {"sortable" : true}
            }'></div>
</div>

<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>