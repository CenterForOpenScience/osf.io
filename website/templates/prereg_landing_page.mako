<%inherit file="base.mako"/>

<%namespace name="erpc" file="erpc_landing_info.mako"/>
<%namespace name="prereg" file="prereg_landing_info.mako"/>

<%def name="description()"> 
    <%
        if campaign_short == 'erpc':
            return erpc.description()
        elif campaign_short == 'prereg':
            return prereg.description()
    %>
</%def>

<%def name="kind()">
    <%
      if campaign_short == 'erpc':
         return erpc.kind()
      elif campaign_short == 'prereg':
          return prereg.kind()
    %>
</%def>

<%def name="steps()"> 
  <%
      if campaign_short == 'erpc':
         return erpc.steps()
      elif campaign_short == 'prereg':
          return prereg.steps()
  %>
</%def>

<%def name="title()">OSF ${campaign_long}</%def>

<%def name="stylesheets()">
    ${ parent.stylesheets() }
    <link rel="stylesheet" href="/static/css/prereg.css">
</%def>

<%def name="javascript_bottom()">
    ${ parent.javascript_bottom() }
    <script src=${"/static/public/js/prereg-landing-page.js" | webpack_asset}></script>
</%def>

<%def name="newPrereg(size=None)">
<% size = size or '' %>
<div id="newPrereg${size}" class="prereg-new-prereg p-md osf-box box-round clearfix m-b-lg" style="display:none">
  <p>Please provide a title for your project: </p>
  <input type="text" class="new-project-title form-control" placeholder="Title">
  <button type="submit" id="newProject${size}" class="btn btn-primary pull-right m-t-md">Continue <i class="fa fa-angle-right"></i></button>
</div>
</%def>

<%def name="existingPrereg(size=None)">
<% size = size or '' %>
<div id="existingPrereg${size}" class="prereg-existing-prereg p-md osf-box box-round clearfix m-b-lg" style="display:none; width: 100%;">
  <p>Go to an existing preregistration:</p>
    <input id="regDraftSearch${size}" class="form-control"></input>
    <div class="p-xs"><a href="#" class="regDraftButton btn btn-primary disabled pull-right">Preregister</a></div>
</div>
</%def>

<%def name="existingProject(size=None)">
<% size = size or '' %>
<div id="existingProject${size}" class="prereg-existing-project p-md osf-box box-round clearfix m-b-lg" style="display:none">
  <p>Preregister an existing project:</p>
  <input id="projectSearch${size}" class="form-control" ></input>
  <div class="p-xs"><a href="#" class="projectRegButton btn btn-primary disabled pull-right">Preregister</a></div>
</div>
</%def>

<%def name="content()">
<div class="prereg-container">
    <h1 class="m-t-xl m-b-lg text-center">Welcome to the ${campaign_long}!</h1>
    <p>${description()}</p>
    <p class="m-t-lg f-w-lg">Ready for the Challenge?</p>
    <p>
        ${steps()}
    </p>
    <div class="col-md-12 visible-xs">                  
      ## Always displayed
      <div class="row">
        <div class="prereg-button m-b-md p-md osf-box-lt p-md box-round prereg" data-qtoggle-group="prereg" data-qtoggle-target="#newPreregXS">Start a new preregistration</div>
        <div class="col-md-12">  
          ${newPrereg('XS')}
        </div>
      </div>
      %if has_draft_registrations:
      <div class="row">
        <div class="prereg-button m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingPreregXS">Continue working on an existing preregistration</div>
        <div class="col-md-12 prereg-button-content-xs">
          ${existingPrereg('XS')}
        </div>
      </div>
      %endif
      %if has_projects:
      <div class="row">
        <div class="prereg-button m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingProjectXS">Preregister a project you already have on the OSF
        </div>
        <div class="col-md-12 prereg-button-content-xs">
          ${existingProject('XS')}
        </div>
      </div>
      %endif      
    </div>
    <div class="row hidden-xs">
      <%
           if has_draft_registrations and has_projects:
               # all three buttons
               num_cols = 3
           elif has_draft_registrations or has_projects:
               # two buttons
               num_cols = 2
           else:
               # one button
               num_cols = 1
      %>
      <table class="prereg-button-row">
        <tbody>
          <tr>
            ## Always displayed
            <td class="col-sm-${ num_cols } prereg-button-col">
              <div class="prereg-button m-b-md p-md osf-box-lt p-md box-round prereg" data-qtoggle-group="prereg" data-qtoggle-target="#newPrereg">Start a new ${kind()}</div>
            </td>
            %if has_draft_registrations:
            <td class="col-sm-${ num_cols } prereg-button-col">
              <div class="prereg-button m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingPrereg">Continue working on an existing ${kind()}</div>
            </td>
            %endif
            %if has_projects:
            <td class="col-sm-${ num_cols } prereg-button-col">
              <div class="prereg-button m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingProject">Make a ${kind()} for a project you already have on the OSF</div>
            </td>
            %endif
          </tr>
          <tr>
            ## Always displayed
            <td class="col-sm-${ num_cols } prereg-button-contents">
              ${newPrereg()}
            </td>
            %if has_draft_registrations:
            <td class="col-sm-${ num_cols } prereg-button-contents">
              ${existingPrereg()}
            </td>
            %endif
            %if has_projects:
            <td class="col-sm-${ num_cols } prereg-button-contents">
              ${existingProject()}
            </td>
            %endif
          </tr>
        </tbody>
      </table>
    </div>
</div>
<%include file="components/autocomplete.mako"/>
<script type="text/javascript">
  window.contextVars = window.contextVars || {};
  window.contextVars.campaign = ${campaign_short | sjson};
</script>
</%def>
