<%inherit file="base.mako"/>
<%namespace name="render_nodes" file="util/render_nodes.mako" />
<%def name="title()">${profile["fullname"]}</%def>
<%def name="stylesheets()">
   ${parent.stylesheets()}
   <link rel="stylesheet" href='/static/css/pages/profile-page.css'>
</%def>

<%def name="javascript_bottom()">
% if user['is_profile']:
    <%include file="profile/modal_change_avatar.mako"/>
% endif
<script src=${"/static/public/js/profile-page.js" | webpack_asset}></script>

</%def>

<%def name="content()">
% if profile['is_merged']:
<div class="alert alert-info">This account has been merged with <a class="alert-link" href="${profile['merged_by']['url']}">${profile['merged_by']['absolute_url']}</a>
</div>
% endif


<div class="page-header">
    <div class="profile-fullname">
        <span>
            % if user['is_profile']:
                <a href="#changeAvatarModal" data-toggle="modal"><img class='profile-gravatar' src="${profile['gravatar_url']}"
                        rel="tooltip" title="Click to change avatar"/></a>
            % else:
                <img class='profile-gravatar' src="${profile['gravatar_url']}"/>
            % endif
        </span>
        <span id="profileFullname" class="h1 overflow m-l-sm">
            ${profile["fullname"]}
        </span>
        <span class="edit-profile-settings">
            % if user['is_profile']:
                <a href="/settings/"><i class="fa fa-pencil m-r-xs"></i> Edit your profile</a>
            % endif
        </span>
    </div>
</div><!-- end-page-header -->


<div class="row">

    <div class="col-sm-6">

        <table class="table table-plain">
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
        <h2>
           ${profile['activity_points'] or "No"} activity point${'s' if profile['activity_points'] != 1 else ''}<br />
           ${profile["number_projects"]} project${'s' if profile["number_projects"] != 1  else ''}, ${profile["number_public_projects"]} public
        </h2>
    </div>

    <div class="col-sm-6">


        <ul class="nav nav-tabs">
            <li class="active"><a href="#social" data-toggle="tab">Social</a></li>
            <li><a href="#jobs" data-toggle="tab">Employment</a></li>
            <li><a href="#schools" data-toggle="tab">Education</a></li>
        </ul>

        <div class="tab-content" id="containDrag">

            <div class="m-t-md tab-pane active" id="social">
                <div data-bind="template: {name: 'profileSocial'}"></div>
            </div>

            <div class="m-t-md tab-pane" id="jobs">
                <div data-bind="template: {name: 'profileJobs'}"></div>
            </div>

            <div class="m-t-md tab-pane" id="schools">
                <div data-bind="template: {name: 'profileSchools'}"></div>
            </div>

        </div>

    </div>

</div>
<hr />
<div class="row">
    <div class="col-sm-6">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
              <h3 class="panel-title" >Public projects</h3>
            </div>
            <div class="panel-body clearfix" id="publicProjects">
                <div class="ball-pulse ball-scale-blue text-center">
                  <div></div>
                  <div></div>
                  <div></div>
                </div>
            </div>
        </div>
    </div>
    <div class="col-sm-6">
        <div class="panel panel-default">
            <div class="panel-heading clearfix">
                <h3 class="panel-title">Public components</h3>
            </div>
            <div class="panel-body clearfix" id="publicComponents">
              <div class="ball-pulse ball-scale-blue text-center">
                <div></div>
                <div></div>
                <div></div>
              </div>
            </div>
        </div>
    </div>
</div><!-- end row -->

<%include file="include/profile/social.mako" />
<%include file="include/profile/jobs.mako" />
<%include file="include/profile/schools.mako" />
<script type="text/javascript">
  (function() {
      var socialUrls = {
          crud: ${ api_url_for('serialize_social', uid=profile['id']) | sjson, n }
      };
      var jobsUrls = {
          crud: ${ api_url_for('serialize_jobs', uid=profile['id']) | sjson, n }
      };
      var schoolsUrls = {
          crud: ${ api_url_for('serialize_schools', uid=profile['id']) | sjson, n }
      };

      window.contextVars = $.extend(true, {}, window.contextVars, {
          socialUrls: socialUrls,
          jobsUrls: jobsUrls,
          schoolsUrls: schoolsUrls,
          user: ${ user | sjson, n },
      });
  })();
</script>

</%def>
