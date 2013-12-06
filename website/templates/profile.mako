<%inherit file="base.mako"/>
<%def name="title()">${fullname}'s Profile</%def>

<%def name="javascript_bottom()">
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
                    $(".fullname").text(data['name']);
                }
            });
        });
    </script>
% endif

</%def>

<%def name="content()">
% if user_is_merged:
<div class="alert alert-info">This account has been merged with <a class="alert-link" href="${user_merged_by_url}">${user_merged_by_url}</a>
</div>
% endif


<div class="page-header">
    <img src="${gravatar_url}" />
    <h1 id="${'profile-fullname' if user_is_profile else ''}" style="display:inline-block">${fullname}</h1>
</div><!-- end-page-header -->

<div class="row">
    <div class="col-md-4">
        <table class="table table-plain">
            <tr>
              <td>Name</td>
              <td class="${'fullname' if user_is_profile else ''}">${fullname}</td>
            </tr>
            <tr>
              <td>Member Since</td>
              <td>${date_registered}</td>
            </tr>
            <tr>
              <td>Public Profile</td>
              <td><a href="/${user_id}/">${user_abs_url}</a></td>
            </tr>
        </table>
    </div>
    <div class="col-md-4 col-md-offset-4">
        <h2>
           ${activity_points or "No"} activity point${'s' if activity_points != 1 else ''}<br />
           ${number_projects} project${'s' if number_projects != 1  else ''}, ${number_public_projects} public
        </h2>
    </div>
</div><!-- end row -->
<hr />

<div class="row">
    <div class="col-md-6">
        <h3>Public Projects</h3>
        <div mod-meta='{
                "tpl" : "util/render_nodes.mako",
                "uri" : "/api/v1/profile/${user_id}/public_projects/",
                "replace" : true,
                "kwargs" : {"sortable" : true}
            }'></div>
    </div>
    <div class="col-md-6">
        <h3>Public Components</h3>
        <div mod-meta='{
                "tpl" : "util/render_nodes.mako",
                "uri" : "/api/v1/profile/${user_id}/public_components/",
                "replace" : true,
                "kwargs" : {"sortable" : true}
            }'></div>
    </div>
</div><!-- end row -->
</%def>
