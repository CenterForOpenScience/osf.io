
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
                mode: "inline",
                success: function(data) {
                    // Also change the display name in the user info table
                    $("td.fullname").text(data['name']);
                }
            });
        });
    </script>
    % endif
    <img src="${gravatar_url}" />
    <h1 id="${'profile-fullname' if user_is_profile else ''}" style="display:inline-block">${fullname}</h1>

</div><!-- end-page-header -->

<div class="row">
    <div class="col-md-4">
        <table class="table plain">
            <tr>
              <td>Name</td>
              <td class="${'fullname' if user_is_profile else ''}">${fullname}</td>
            </tr>
            <tr>
                <td>Location</td>
                <td></td>
            </tr>
            <tr>
              <td>Member Since</td>
              <td>${date_registered}</td>
            </tr>
            <tr>
              <td>Public Profile</td>
              <td><a href="/profile/${user_id}/">/profile/${user_id}/</a></td>
            </tr>
        </table>
    </div>
    <div class="col-md-4">&nbsp;</div>
    <div class="col-md-4">
        <h2>
           ${activity_points} activity point${'s' if activity_points != 1 else ''}<br />
           ##${number_projects} project${'s' if number_projects !=1  else ''}, ${number_public_projects} public
        </h2>
    </div>
</div><!-- end row -->
<hr />

<div class="row">
    <div class="col-md-6">
        <h3>Public Projects</h3>
        <div mod-meta='{
                "tpl" : "util/render_nodes.html",
                "uri" : "/api/v1/profile/${user_id}/public_projects/",
                "replace" : true,
                "kwargs" : {"sortable" : true}
            }'>
        </div>
    </div>
    <div class="col-md-6">
        <h3>Public Components</h3>
        <div mod-meta='{
                "tpl" : "util/render_nodes.html",
                "uri" : "/api/v1/profile/${user_id}/public_components/",
                "replace" : true,
                "kwargs" : {"sortable" : true}
            }'></div>
    </div>
</div>

<div mod-meta='{"tpl": "footer.mako", "replace": true}'></div>
