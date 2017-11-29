<%inherit file="base.mako"/>


<%def name="title()">OSF Prereg Challenge</%def>

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
  <p class="prereg-text-left">Please provide a title for your project: </p>
  <input type="text" class="new-project-title form-control" placeholder="Title">
  <button type="submit" id="newProject${size}" class="btn btn-primary pull-right m-t-md">Continue <i class="fa fa-angle-right"></i></button>
</div>
</%def>

<%def name="existingPrereg(size=None)">
<% size = size or '' %>
<div id="existingPrereg${size}" class="prereg-existing-prereg p-md osf-box box-round clearfix m-b-lg" style="display:none; width: 100%;">
  <p class="prereg-text-left">Go to an existing preregistration:</p>
    <input id="regDraftSearch${size}" class="form-control"></input>
    <div class="p-xs"><a href="#" class="regDraftButton btn btn-primary disabled pull-right">Preregister</a></div>
</div>
</%def>

<%def name="existingProject(size=None)">
<% size = size or '' %>
<div id="existingProject${size}" class="prereg-existing-project p-md osf-box box-round clearfix m-b-lg" style="display:none">
  <p class="prereg-text-left">Preregister an existing project:</p>
  <input id="projectSearch${size}" class="form-control" ></input>
  <div class="p-xs"><a href="#" class="projectRegButton btn btn-primary disabled pull-right">Preregister</a></div>
</div>
</%def>

<%def name="content()">
<div class="prereg-container">
    <h1 class="m-t-xl m-b-lg text-center">
        <img class="prereg-logo" src="/static/img/registries/osf-prereg-black.png" alt="preregistration_challenge_logo">
    </h1>
    <p>Improve your research with preregistration. </p>
    <p>The process of creating a <a href='http://www.cos.io/prereg'> preregistration</a> is beneficial to both the scientific field and to you, the scientist. By writing out detailed data collection methods, analysis plans, and rules for excluding or missing data, you can make important decisions that affect your workflow earlier, without the biases that occur once the data are in front of you.</p>

    <div class="col-md-12 visible-xs">                  
      %if is_logged_in:
      <div class="row">
        <div class="prereg-button-xs prereg-button prereg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round prereg" data-qtoggle-group="prereg" data-qtoggle-target="#newPreregXS">Start a new preregistration</div>
        <div class="prereg-button-content-xs">  
          ${newPrereg('XS')}
        </div>
      </div>
      %else:
      <a href="${domain}login/?campaign=prereg">
          <div class="prereg-button-xs prereg-button m-b-md p-md osf-box-lt p-md box-round">Preregister</div>
      </a>
      %endif
      %if has_draft_registrations:
      <div class="row">
        <div class="prereg-button-xs prereg-button prereg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingPreregXS">Continue working on an existing draft preregistration</div>
        <div class="prereg-button-content-xs">
          ${existingPrereg('XS')}
        </div>
      </div>
      %endif
      %if has_projects:
      <div class="row">
        <div class="prereg-button-xs prereg-button prereg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingProjectXS">Preregister a project you already have on the OSF
        </div>
        <div class="prereg-button-content-xs">
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
            %if is_logged_in:
            <div>
            <td class="col-sm-${ num_cols } prereg-button-col">
              <div class="prereg-button prereg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round prereg" data-qtoggle-group="prereg" data-qtoggle-target="#newPrereg">Start a new pregistration</div>
            </td>
            %else:
            <td class="col-sm-${ num_cols } prereg-button-col">
              <a href="${domain}login/?campaign=prereg">
                <div class="prereg-button m-b-md p-md osf-box-lt p-md box-round">Preregister</div>  
              </a>
            </td>
            %endif
            %if has_draft_registrations:
            <td class="col-sm-${ num_cols } prereg-button-col">
              <div class="prereg-button prereg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingPrereg">Continue working on an existing draft preregistration</div>
            </td>
            %endif
            %if has_projects:
            <td class="col-sm-${ num_cols } prereg-button-col">
              <div class="prereg-button prereg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="prereg" data-qtoggle-target="#existingProject">Preregister a project you already have on the OSF</div>
            </td>
            %endif
          </tr>
          <tr>
            ## Always displayed
            <td class="col-sm-${ num_cols } prereg-button-contents">
              <div class="prereg-action"> 
                ${newPrereg()}
              </div>
            </td>
            %if has_draft_registrations:
            <td class="col-sm-${ num_cols } prereg-button-contents">
              <div class="prereg-action"> 
                ${existingPrereg()}
              </div>
            </td>
            %endif
            %if has_projects:
            <td class="col-sm-${ num_cols } prereg-button-contents">
              <div class="prereg-action"> 
                ${existingProject()}
              </div>
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
