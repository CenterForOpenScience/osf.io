<%inherit file="base.mako"/>
<%def name="title()">${profile["fullname"]}</%def>

<%def name="javascript_bottom()">

<script>
    % if user["is_profile"]:
        $.fn.editable.defaults.mode = 'inline';
        $(function() {
            $('#profile-fullname > span').editable({
                type:  'text',
                pk:    '${profile["id"]}',
                name:  'fullname',
                url:   '/api/v1/profile/${profile["id"]}/edit/',
                title: 'Edit Full Name',
                placement: 'bottom',
                value: '${profile["fullname"] | js_str}',
                success: function(data) {
                    // Also change the display name in the user info table
                    $(".fullname").text(data['name']);
                }
            });

            var gravatar = $('#profile-gravatar');
        });
    % endif
##    TODO: Make the following modules CommonJS-compatible:
##    $script(['/static/addons/badges/bake-badges.js'], 'bakery');
##    $script(['/static/addons/badges/badge-popover.js'], 'display');
</script>
% if user['is_profile']:
    <%include file="profile/modal_change_avatar.mako"/>
% endif

</%def>

<%def name="content()">
% if profile['is_merged']:
<div class="alert alert-info">This account has been merged with <a class="alert-link" href="${profile['merged_by']['url']}">${profile['merged_by']['absolute_url']}</a>
</div>
% endif


<div class="page-header">
    <a href="#changeAvatarModal" data-toggle="modal">
        % if user['is_profile']:
            <img id='profile-gravatar' src="${profile['gravatar_url']}"
                rel="tooltip" title="click to change avatar"/>
        % else:
             <img id='profile-gravatar' src="${profile['gravatar_url']}"/>
        % endif
    </a>
    <h1 id="profile-fullname"><span class="overflow">${profile["fullname"]}</span></h1>
</div><!-- end-page-header -->


<div class="row">

    <div class="col-md-6">


        <div>
            <table class="table table-plain">
                <tr>
                  <td>Name</td>
                  <td class="fullname overflow-block" width="300px">${profile["fullname"]}</td>
                </tr>
                % if profile.get('date_registered'):
                    <tr>
                        <td>Member&nbsp;Since</td>
                        <td>${profile['date_registered']}</td>
                    </tr>
                % endif
                % if profile.get('url') and profile.get('display_absolute_url'):
                    <tr>
                        <td>Public&nbsp;Profile</td>
                        <td><a href="${profile['url']}">${profile['display_absolute_url']}</a></td>
                    </tr>
                % endif
            </table>
        </div>
        <div>
            <h2>
               ${profile['activity_points'] or "No"} activity point${'s' if profile['activity_points'] != 1 else ''}<br />
               ${profile["number_projects"]} project${'s' if profile["number_projects"] != 1  else ''}, ${profile["number_public_projects"]} public
            </h2>
        </div>


    </div>

    <div class="col-md-6">


        <ul class="nav nav-tabs">
            <li class="active"><a href="#social" data-toggle="tab">Social</a></li>
            <li><a href="#jobs" data-toggle="tab">Employment</a></li>
            <li><a href="#schools" data-toggle="tab">Education</a></li>
        </ul>

        <div class="tab-content" id="containDrag">

            <div class="tab-pane active" id="social">
                <div data-bind="template: {name: 'profileSocial'}"></div>
            </div>

            <div class="tab-pane" id="jobs">
                <div data-bind="template: {name: 'profileJobs'}"></div>
            </div>

            <div class="tab-pane" id="schools">
                <div data-bind="template: {name: 'profileSchools'}"></div>
            </div>

        </div>

    </div>

</div>

## TODO: Review and un-comment
## TODO: Render badges w/ Knockout
## TODO: Add profile hooks to add-on core
##<hr />
##
##<div class="row">
##%if badges:
##    <div class="col-md-6">
##        <h3>Badges Endorsed by This User</h3>
##        <div class="badge-list" style="overflow-y:auto; height:250px; padding-top:10px;">
##            %for badge in badges:
##                <div class="media">
##                    <img src="${badge.image}"  width="64px" height="64px" class="open-badge badge-popover media-object pull-left"/>
##                    <div class="media-body">
##                        <h4 class="media-heading">${badge.name}<small> ${badge.description}</small></h4>
##                        ${badge.criteria_list}
##                    </div>
##                </div>
##            %endfor
##        </div>
##    </div>
##    <div class="col-md-6">
##%else:
##    <div class="col-md-12">
##%endif
##        <h3>"Sash"</h3>
##        <div class="profile-badge-list">
##            %for assertion in reversed(assertions):
##            <div>
##                <img src="${assertion.badge.image}" width="64px" height="64px" class="open-badge badge-popover" badge-url="/badge/assertion/json/${assertion._id}/" data-content="${assertion.badge.description_short}" data-toggle="popover" data-title="<a href=&quot;/${assertion.badge._id}/&quot;>${assertion.badge.name}</a>
##                %if not assertion.badge.is_system_badge:
##                    - <a href=&quot;${assertion.badge.creator.owner.profile_url}&quot;>${assertion.badge.creator.owner.fullname}</a>"/>
##                %else:
##                    "/>
##                %endif
##                <br/>
##                <span class="badge">${assertion.amount}<span>
##            </div>
##            %endfor
##        </div>
##    </div>
##</div>

<hr />
<div class="row">
    <div class="col-md-6">
        <h3>Public Projects</h3>
        <div mod-meta='{
                "tpl" : "util/render_nodes.mako",
                "uri" : "/api/v1/profile/${profile["id"]}/public_projects/",
                "replace" : true,
                "kwargs" : {"sortable" : true}
            }'></div>
    </div>
    <div class="col-md-6">
        <h3>Public Components</h3>
        <div mod-meta='{
                "tpl" : "util/render_nodes.mako",
                "uri" : "/api/v1/profile/${profile["id"]}/public_components/",
                "replace" : true,
                "kwargs" : {"sortable" : true}
            }'></div>
    </div>
</div><!-- end row -->

<%include file="_log_templates.mako"/>
<%include file="include/profile/social.mako" />
<%include file="include/profile/jobs.mako" />
<%include file="include/profile/schools.mako" />
<script type="text/javascript">
  (function() {
      var socialUrls = {
          crud: '${ api_url_for('serialize_social', uid=profile['id']) }'
      };
      var jobsUrls = {
          crud: '${ api_url_for('serialize_jobs', uid=profile['id']) }'
      };
      var schoolsUrls = {
          crud: '${ api_url_for('serialize_schools', uid=profile['id']) }'
      };

      window.contextVars = $.extend(true, {}, window.contextVars, {
          socialUrls: socialUrls,
          jobsUrls: jobsUrls,
          schoolsUrls: schoolsUrls
      });
  })();
</script>
<script src="/static/public/js/profile-page.js"></script>

</%def>
