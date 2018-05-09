<%inherit file="base.mako"/>


<%def name="title()">Registered Reports</%def>

<%def name="stylesheets()">
    ${ parent.stylesheets() }
    <link rel="stylesheet" href="/static/css/registration_landing.css">
</%def>

<%def name="javascript_bottom()">
    ${ parent.javascript_bottom() }
    <script src=${"/static/public/js/reg-landing-page.js" | webpack_asset}></script>
</%def>

<%def name="newReg(size='')">
<div id="newReg${size}" class="p-md osf-box box-round clearfix m-b-lg" style="display:none">
  <p class="reg-landing-page-text-left">Please provide a title for your project: </p>
  <input type="text" class="new-project-title form-control" placeholder="Title">
  <button type="submit" id="newProject${size}" class="btn btn-primary pull-right m-t-md">Create</button>
</div>
</%def>

<%def name="existingDraft(size='')">
<div id="existingDraft${size}" class="p-md osf-box box-round clearfix m-b-lg" style="display:none; width: 100%;">
  <p class="reg-landing-page-text-left">Go to an existing registration:</p>
    <input id="regDraftSearch${size}" class="form-control"></input>
    <div class="p-xs"><a href="#" class="regDraftButton btn btn-primary m-t-sm disabled pull-right">Continue</a></div>
</div>
</%def>

<%def name="existingProject(size='')">
<div id="existingProject${size}" class="p-md osf-box box-round clearfix m-b-lg" style="display:none">
  <p class="reg-landing-page-text-left">Register an existing project:</p>
  <input id="projectSearch${size}" class="form-control" ></input>
  <div class="p-xs"><a href="#" class="projectRegButton btn btn-primary m-t-sm disabled pull-right">Register</a></div>
</div>
</%def>

<%def name="content()">
<div class="reg-landing-page-container">
    <h1 class="m-t-xl m-b-lg text-center">
        Simple Registered Report Protocol Preregistration
    </h1>
    <div class="text-center">
        <img class="reg-landing-page-logo m-b-lg" src="/static/img/registries/registered_reports.svg" alt="registered_reports_diagram">
    </div>
    <p>Registered Reports benefit science by improving rigor and reducing publication bias.</p>
    <p>When to use this form:</p>
    <p style="padding-left:1em;">Use this form <b>after</b> you have received “in principle acceptance” (IPA) by a journal following Stage 1 Peer Review, and <b>before</b> you have begun the study.</p>

    <div class="col-md-12 visible-xs">
      %if is_logged_in:
      <div class="row">
        <div class="reg-landing-page-button-xs reg-landing-page-button reg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round reg" data-qtoggle-group="reg" data-qtoggle-target="#newRegXS">Submit your approved Registered Report</div>
        <div class="reg-landing-page-button-content-xs">
          ${newReg('XS')}
        </div>
      </div>
      %else:
      <a href="${domain}login/">
          <div class="reg-landing-page-button-xs reg-landing-page-button m-b-md p-md osf-box-lt p-md box-round">Register</div>
      </a>
      %endif
      %if has_draft_registrations:
      <div class="row">
        <div class="reg-landing-page-button-xs reg-landing-page-button reg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="reg" data-qtoggle-target="#existingDraftXS">Continue working on an existing registration draft</div>
        <div class="reg-landing-page-button-content-xs">
          ${existingDraft('XS')}
        </div>
      </div>
      %endif
      %if has_projects:
      <div class="row">
        <div class="reg-landing-page-button-xs reg-landing-page-button reg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="reg" data-qtoggle-target="#existingProjectXS">Preregister an analysis plan for an OSF Project
        </div>
        <div class="reg-landing-page-button-content-xs">
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
      <table class="reg-landing-page-button-row">
        <tbody>
          <tr>
            %if is_logged_in:
            <div>
            <td class="col-sm-${ num_cols } reg-landing-page-button-col">
              <div class="reg-landing-page-button reg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round reg" data-qtoggle-group="reg" data-qtoggle-target="#newReg">Submit your approved Registered Report</div>
            </td>
            %else:
            <td class="col-sm-${ num_cols } reg-landing-page-button-col">
              <a href="${domain}login/?campaign=osf-registered-reports&next=${domain}rr">
                <div class="reg-landing-page-button m-b-md p-md osf-box-lt p-md box-round">Create a Registered Report</div>
              </a>
            </td>
            %endif
            %if has_draft_registrations:
            <td class="col-sm-${ num_cols } reg-landing-page-button-col">
              <div class="reg-landing-page-button reg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="reg" data-qtoggle-target="#existingDraft">Continue working on an existing draft of Registered Report</div>
            </td>
            %endif
            %if has_projects:
            <td class="col-sm-${ num_cols } reg-landing-page-button-col">
              <div class="reg-landing-page-button reg-button-qtoggle m-b-md p-md osf-box-lt p-md box-round" data-qtoggle-group="reg" data-qtoggle-target="#existingProject">Preregister an analysis plan for an OSF Project</div>
            </td>
            %endif
          </tr>
          <tr>
            ## Always displayed
            <td class="col-sm-${ num_cols } reg-landing-page-button-contents">
              <div class="reg-landing-page-action">
                ${newReg()}
              </div>
            </td>
            %if has_draft_registrations:
            <td class="col-sm-${ num_cols } reg-landing-page-button-contents">
              <div class="reg-landing-page-action">
                ${existingDraft()}
              </div>
            </td>
            %endif
            %if has_projects:
            <td class="col-sm-${ num_cols } reg-landing-page-button-contents">
              <div class="reg-landing-page-action">
                ${existingProject()}
              </div>
            </td>
            %endif
          </tr>
        </tbody>
      </table>
    </div>
    <div class="text-center">
        You can learn more about Registered Reports <a href="https://cos.io/rr"> here</a>. If you do not have IPA from a journal, you can still preregister your research. Learn more <a href="https://cos.io/prereg"> here</a>.
    </div>

</div>
<%include file="components/autocomplete.mako"/>
<script type="text/javascript">
  window.contextVars = window.contextVars || {};
  window.contextVars.campaign = ${campaign_short | sjson};
</script>
</%def>
